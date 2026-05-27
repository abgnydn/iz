// iz-1 browser-native training loop using fused-lora's WebGPU kernels.
//
// Model: y = (x @ A^T) @ B^T
//   x ∈ R^D_in (7 features from TR-MRV-Bench)
//   A ∈ R^{R × D_in}      (lora_down)
//   B ∈ R^{D_out × R}     (lora_up)
//   D_out = 1 (log CO₂ / year)
//
// Loss: weighted MSE on log-target. Sample weight = label confidence
//   (1.0 disclosure, 0.5 climate_trace, 0.25 sector_default).
//
// Backward + Adam: dispatched entirely on GPU via the existing fused-lora
// shaders (lora_*_bwd_*.wgsl + adam_lora.wgsl). CPU does only minibatch
// orchestration + loss tracking + UI updates.

const $ = (id) => document.getElementById(id);
const status = (msg) => { const el = $("status"); el.textContent = (el.textContent + "\n" + msg).slice(-2400); el.scrollTop = el.scrollHeight; };

const SHADERS = ["lora_down", "lora_up", "lora_down_bwd_A", "lora_up_bwd_B", "lora_up_bwd_temp", "adam_lora"];

// --- WebGPU init --------------------------------------------------------
let device, queue, bench;
const pipelines = {};
const bgls = {};

async function initGPU() {
  if (!navigator.gpu) { status("✗ WebGPU not available — try Chrome 113+ or Safari 18+."); return false; }
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) { status("✗ no adapter"); return false; }
  const features = [];
  if (adapter.features.has("shader-f16")) features.push("shader-f16");
  device = await adapter.requestDevice({ requiredFeatures: features });
  queue = device.queue;
  status(`✓ WebGPU OK — ${adapter.info?.description || adapter.info?.vendor || "device"}, f16=${features.includes("shader-f16")}`);
  return true;
}

async function loadShaders() {
  for (const name of SHADERS) {
    const src = await (await fetch(`./shaders/${name}.wgsl`)).text();
    const mod = device.createShaderModule({ code: src, label: name });
    const info = await mod.getCompilationInfo();
    for (const m of info.messages) {
      if (m.type === "error") {
        status(`✗ ${name}: ${m.message} (line ${m.lineNum})`);
        throw new Error(`shader ${name} failed to compile`);
      }
    }
    const pipe = device.createComputePipeline({ layout: "auto", compute: { module: mod, entryPoint: name } });
    pipelines[name] = pipe;
    bgls[name] = pipe.getBindGroupLayout(0);
  }
  status(`✓ compiled ${SHADERS.length} shaders`);
}

// --- buffer helpers -----------------------------------------------------
// WebGPU buffer sizes must be a multiple of 4 (and ≥ 16 for storage).
function bufStorage(sizeBytes, label) {
  return device.createBuffer({ size: Math.max(pad4Bytes(sizeBytes), 16), usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC, label });
}
function bufUniform(sizeBytes, label) {
  return device.createBuffer({ size: Math.max(pad4Bytes(sizeBytes), 16), usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST, label });
}
function bufRead(sizeBytes, label) {
  return device.createBuffer({ size: Math.max(pad4Bytes(sizeBytes), 16), usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST, label });
}

function f32ToF16Bits(v) {
  const f32 = new Float32Array(1); f32[0] = v;
  const u = new Uint32Array(f32.buffer)[0];
  const sign = (u >>> 31) & 1;
  let exp = ((u >>> 23) & 0xff) - 127 + 15;
  let mant = u & 0x7fffff;
  if (exp <= 0) { exp = 0; mant = 0; }
  else if (exp >= 31) { exp = 31; mant = 0; }
  else mant = mant >> 13;
  return (sign << 15) | (exp << 10) | mant;
}
function f16BitsToF32(h) {
  const sign = (h >> 15) & 1;
  const exp  = (h >> 10) & 0x1f;
  const mant =  h & 0x3ff;
  let f;
  if (exp === 0)      f = mant === 0 ? 0 : (mant / 1024) * Math.pow(2, -14);
  else if (exp === 31) f = mant === 0 ? Infinity : NaN;
  else                 f = (1 + mant / 1024) * Math.pow(2, exp - 15);
  return sign ? -f : f;
}
// WebGPU requires writeBuffer and copyBufferToBuffer sizes to be multiples of
// 4 bytes. Our buffers are all over the place (D=7 → 14 bytes, M=1 → 2 bytes),
// so every f16-payload helper pads up to the next 4-byte boundary.
function pad2(n) { return n + (n & 1); }  // round Uint16 length up to even
function pad4Bytes(n) { return (n + 3) & ~3; }
function toF16Buffer(arr) {
  const u = new Uint16Array(pad2(arr.length));
  for (let i = 0; i < arr.length; i++) u[i] = f32ToF16Bits(arr[i]);
  return u;
}
async function readF16Buffer(buf, n) {
  const bytes = pad4Bytes(n * 2);
  const stage = bufRead(bytes, "stage");
  const enc = device.createCommandEncoder();
  enc.copyBufferToBuffer(buf, 0, stage, 0, bytes);
  queue.submit([enc.finish()]);
  await stage.mapAsync(GPUMapMode.READ);
  const view = new Uint16Array(stage.getMappedRange().slice(0));
  stage.unmap();
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = f16BitsToF32(view[i]);
  return out;
}

// --- bench load + split -------------------------------------------------
async function loadBench() {
  const r = await fetch("./bench.json");
  bench = await r.json();
  status(`✓ bench: ${bench.samples.length} samples, feat_dim=${bench.schema.feat_dim}`);
  const train = bench.samples.filter(s => s.split === "train");
  const val   = bench.samples.filter(s => s.split === "val");
  const test  = bench.samples.filter(s => s.split === "test");
  status(`  train=${train.length}  val=${val.length}  test=${test.length}`);
  return { train, val, test };
}

// --- training -----------------------------------------------------------
class IzModel {
  constructor(D, R, M, yMeanBias = 0) {
    this.D = D; this.R = R; this.M = M;
    this.yMeanBias = yMeanBias;   // target offset — model learns deviation from mean
    // From-scratch (no frozen base) — init BOTH A and B as small Gaussian so
    // gradient flows on step 0. Standard LoRA-on-frozen-base zero-init for B
    // would freeze A's gradient because dL/dtemp = dy * B = 0.
    const stdA = 1 / Math.sqrt(D);
    const stdB = 1 / Math.sqrt(R);
    const rng = () => {
      const u = Math.max(1e-9, Math.random()), v = Math.max(1e-9, Math.random());
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    };
    const A = new Float32Array(R * D);
    for (let i = 0; i < A.length; i++) A[i] = rng() * stdA;
    const B = new Float32Array(M * R);
    for (let i = 0; i < B.length; i++) B[i] = rng() * stdB;
    this.A = bufStorage(R * D * 2, "A"); queue.writeBuffer(this.A, 0, toF16Buffer(A));
    this.B = bufStorage(M * R * 2, "B"); queue.writeBuffer(this.B, 0, toF16Buffer(B));
    this.dA = bufStorage(R * D * 2, "dA");
    this.dB = bufStorage(M * R * 2, "dB");
    this.mA = bufStorage(R * D * 4, "mA");
    this.vA = bufStorage(R * D * 4, "vA");
    this.mB = bufStorage(M * R * 4, "mB");
    this.vB = bufStorage(M * R * 4, "vB");
    // scratch
    this.x = bufStorage(D * 2, "x");
    this.temp = bufStorage(R * 2, "temp");
    this.y = bufStorage(M * 2, "y_hat");
    this.dY = bufStorage(M * 2, "dY");
    this.dtemp = bufStorage(R * 2, "dtemp");
    // uniforms
    this.uDownF = bufUniform(8, "lora_down_args");  // { K, RANK }
    queue.writeBuffer(this.uDownF, 0, new Uint32Array([D, R]));
    this.uUpF = bufUniform(16, "lora_up_args");    // { RANK, M, scale, _pad }
    queue.writeBuffer(this.uUpF, 0, new Uint32Array([R, M, 0, 0]));
    queue.writeBuffer(this.uUpF, 8, new Float32Array([1.0]));
    this.uUpBwdB = this.uUpF;
    this.uUpBwdT = this.uUpF;
    this.uDownBwdA = this.uDownF;
    this.adamUA = bufUniform(32, "adam_A_args");
    this.adamUB = bufUniform(32, "adam_B_args");
    this.step = 0;
  }

  bg(pipe, buffers) {
    const entries = buffers.map((b, i) => ({ binding: i, resource: { buffer: b } }));
    return device.createBindGroup({ layout: pipe.getBindGroupLayout(0), entries });
  }

  zero(buf, sizeBytes) {
    queue.writeBuffer(buf, 0, new Uint8Array(pad4Bytes(sizeBytes)));
  }

  forward(xArr) {
    queue.writeBuffer(this.x, 0, toF16Buffer(xArr));
    this.zero(this.y, this.M * 2);
    const enc = device.createCommandEncoder();
    {
      const p = enc.beginComputePass();
      p.setPipeline(pipelines.lora_down);
      p.setBindGroup(0, this.bg(pipelines.lora_down, [this.temp, this.x, this.A, this.uDownF]));
      p.dispatchWorkgroups(this.R, 1, 1);
      p.end();
    }
    {
      const p = enc.beginComputePass();
      p.setPipeline(pipelines.lora_up);
      p.setBindGroup(0, this.bg(pipelines.lora_up, [this.y, this.temp, this.B, this.uUpF]));
      p.dispatchWorkgroups(Math.ceil(this.M / 64), 1, 1);
      p.end();
    }
    queue.submit([enc.finish()]);
  }

  // Backward: given dL/dy (scalar weighted error), compute dA + dB and Adam-step.
  async stepBackward(dy_scalar, lr, beta1, beta2, eps) {
    this.step++;
    queue.writeBuffer(this.dY, 0, toF16Buffer([dy_scalar]));
    // Bwd: B
    this.zero(this.dB, this.M * this.R * 2);
    {
      const enc = device.createCommandEncoder();
      const p = enc.beginComputePass();
      p.setPipeline(pipelines.lora_up_bwd_B);
      p.setBindGroup(0, this.bg(pipelines.lora_up_bwd_B, [this.dB, this.dY, this.temp, this.uUpBwdB]));
      p.dispatchWorkgroups(Math.ceil(this.M / 64), 1, 1);
      p.end();
      queue.submit([enc.finish()]);
    }
    // Bwd: dtemp
    {
      const enc = device.createCommandEncoder();
      const p = enc.beginComputePass();
      p.setPipeline(pipelines.lora_up_bwd_temp);
      p.setBindGroup(0, this.bg(pipelines.lora_up_bwd_temp, [this.dtemp, this.dY, this.B, this.uUpBwdT]));
      p.dispatchWorkgroups(this.R, 1, 1);
      p.end();
      queue.submit([enc.finish()]);
    }
    // Bwd: dA
    this.zero(this.dA, this.R * this.D * 2);
    {
      const enc = device.createCommandEncoder();
      const p = enc.beginComputePass();
      p.setPipeline(pipelines.lora_down_bwd_A);
      p.setBindGroup(0, this.bg(pipelines.lora_down_bwd_A, [this.dA, this.dtemp, this.x, this.uDownBwdA]));
      p.dispatchWorkgroups(Math.ceil(this.D / 64), this.R, 1);
      p.end();
      queue.submit([enc.finish()]);
    }
    // Adam on A and B
    const bc1 = 1 - Math.pow(beta1, this.step);
    const bc2 = 1 - Math.pow(beta2, this.step);
    // adam_lora.wgsl args: { N, _pad, lr, beta1, beta2, eps, bc1, bc2 }
    const adamA_args = new ArrayBuffer(32);
    new Uint32Array(adamA_args, 0, 2).set([this.R * this.D, 0]);
    new Float32Array(adamA_args, 8, 6).set([lr, beta1, beta2, eps, bc1, bc2]);
    queue.writeBuffer(this.adamUA, 0, adamA_args);
    const adamB_args = new ArrayBuffer(32);
    new Uint32Array(adamB_args, 0, 2).set([this.M * this.R, 0]);
    new Float32Array(adamB_args, 8, 6).set([lr, beta1, beta2, eps, bc1, bc2]);
    queue.writeBuffer(this.adamUB, 0, adamB_args);
    {
      const enc = device.createCommandEncoder();
      const pA = enc.beginComputePass();
      pA.setPipeline(pipelines.adam_lora);
      pA.setBindGroup(0, this.bg(pipelines.adam_lora, [this.A, this.dA, this.mA, this.vA, this.adamUA]));
      pA.dispatchWorkgroups(Math.ceil((this.R * this.D) / 64), 1, 1);
      pA.end();
      const pB = enc.beginComputePass();
      pB.setPipeline(pipelines.adam_lora);
      pB.setBindGroup(0, this.bg(pipelines.adam_lora, [this.B, this.dB, this.mB, this.vB, this.adamUB]));
      pB.dispatchWorkgroups(Math.ceil((this.M * this.R) / 64), 1, 1);
      pB.end();
      queue.submit([enc.finish()]);
    }
  }

  async predict(xArr) {
    this.forward(xArr);
    const y = await readF16Buffer(this.y, this.M);
    return y[0] + this.yMeanBias;
  }
}

// --- loss plot ----------------------------------------------------------
const lossHistory = { train: [], val: [] };
function drawLoss() {
  const c = $("loss-canvas");
  const ctx = c.getContext("2d");
  const W = c.width, H = c.height;
  ctx.clearRect(0, 0, W, H);
  const all = [...lossHistory.train, ...lossHistory.val].filter(Number.isFinite);
  if (all.length === 0) return;
  const ymax = Math.max(...all) * 1.05;
  const ymin = 0;
  const N = Math.max(lossHistory.train.length, lossHistory.val.length, 1);
  const xfor = i => 10 + (i / Math.max(1, N - 1)) * (W - 20);
  const yfor = v => H - 10 - ((v - ymin) / (ymax - ymin || 1)) * (H - 20);
  const plot = (arr, color) => {
    if (arr.length < 2) return;
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath();
    for (let i = 0; i < arr.length; i++) {
      const x = xfor(i), y = yfor(arr[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  };
  plot(lossHistory.train, "#b85c3f");
  plot(lossHistory.val, "#2d5a4c");
}

// --- run ---------------------------------------------------------------
async function train() {
  const R = parseInt($("rank").value, 10);
  const lr = parseFloat($("lr").value);
  const epochs = parseInt($("epochs").value, 10);
  const batch = parseInt($("batch").value, 10);
  const D = bench.schema.feat_dim;
  const M = 1;
  const mean = bench.schema.feat_mean;
  const sd = bench.schema.feat_std;
  const norm = (f) => f.map((v, i) => (v - mean[i]) / sd[i]);

  const train = bench.samples.filter(s => s.split === "train");
  const val = bench.samples.filter(s => s.split === "val");
  if (train.length === 0) { status("no train samples"); return; }

  // Physics-informed target: subtract per-sample y_prior_log (cap × EF × cf
  // formula in log space) so the model learns residuals against the prior.
  // Falls back to yMean if y_prior_log is missing on a sample.
  const yMean = train.reduce((a, s) => a + s.y_log, 0) / train.length;
  const usePrior = train.every(s => typeof s.y_prior_log === "number" && isFinite(s.y_prior_log));
  status(`begin training: R=${R} lr=${lr} epochs=${epochs} batch=${batch} D=${D}  ${usePrior ? "per-sample prior" : `yMean=${yMean.toFixed(2)}`}`);

  // Model uses 0 bias when per-sample prior is active; bias added at predict time.
  const model = new IzModel(D, R, M, usePrior ? 0 : yMean);
  lossHistory.train.length = 0; lossHistory.val.length = 0;

  // Best-checkpoint tracking — guards against late-training gradient spikes.
  let bestVL = Infinity;
  let bestA = null;
  let bestB = null;
  let bestEp = 0;

  $("train-btn").disabled = true;
  const t0 = performance.now();
  for (let ep = 1; ep <= epochs; ep++) {
    // shuffle indices
    const idx = train.map((_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }

    let losses = [];
    for (const i of idx) {
      const s = train[i];
      const x = norm(s.feat);
      model.forward(x);
      const yhatRaw = (await readF16Buffer(model.y, 1))[0];
      // Residual target: y_log − per-sample prior (physics-informed) or yMean fallback.
      const bias = usePrior ? s.y_prior_log : yMean;
      const target = s.y_log - bias;
      const err = yhatRaw - target;
      const loss = 0.5 * err * err * s.w;
      losses.push(loss);
      await model.stepBackward(err * s.w, lr, 0.9, 0.999, 1e-8);
    }
    const trL = losses.reduce((a, b) => a + b, 0) / losses.length;
    lossHistory.train.push(trL);

    // val pass — predict() returns yhatRaw + model.yMeanBias; if usePrior, add
    // per-sample prior on top instead.
    let vMae = 0; let vn = 0;
    for (const s of val) {
      const yhat = await model.predict(norm(s.feat));
      const yhatFinal = usePrior ? yhat + s.y_prior_log : yhat;
      vMae += Math.abs(yhatFinal - s.y_log); vn++;
    }
    const vL = vn ? vMae / vn : NaN;
    lossHistory.val.push(vL);

    $("train-loss").innerHTML = `${trL.toFixed(4)} <small>MSE on log-CO₂</small>`;
    $("val-mae").textContent = isFinite(vL) ? vL.toFixed(4) : "—";
    $("step").textContent = `${ep} / ${epochs}`;
    drawLoss();
    if (ep % 10 === 0) status(`ep ${ep}  trL=${trL.toFixed(4)}  vMAE=${vL.toFixed(4)}`);

    // Snapshot best-val weights to defend against late-training spikes
    if (isFinite(vL) && vL < bestVL && ep >= 10) {
      bestVL = vL;
      bestEp = ep;
      bestA = await readF16Buffer(model.A, model.R * model.D);
      bestB = await readF16Buffer(model.B, model.M * model.R);
    }

    // yield to UI
    await new Promise(r => setTimeout(r, 0));
  }
  const t1 = performance.now();
  status(`✓ training done in ${((t1 - t0) / 1000).toFixed(1)}s`);

  // Restore best-val weights for test predictions
  if (bestA && bestB) {
    queue.writeBuffer(model.A, 0, toF16Buffer(bestA));
    queue.writeBuffer(model.B, 0, toF16Buffer(bestB));
    status(`✓ restored best-val weights from ep ${bestEp} (vMAE=${bestVL.toFixed(4)})`);
  }

  // test set predictions
  const test = bench.samples.filter(s => s.split === "test");
  const body = $("preds-body");
  body.innerHTML = "";
  const SCOPES = ["cement", "steel", "aluminum", "fertilizer"];
  for (const s of test) {
    const yhat = await model.predict(norm(s.feat));
    const yhatFinal = usePrior ? yhat + s.y_prior_log : yhat;
    const truth = s.y_raw;
    const pred = Math.expm1(yhatFinal);
    const ratio = (pred / truth);
    const eu = s.eu_default || 0;
    const reductionPct = eu > 0 ? ((eu - pred) / eu) * 100 : 0;
    const scopeIdx = s.feat.slice(3).findIndex(v => v === 1);
    const scopeName = SCOPES[scopeIdx] || "?";
    const row = document.createElement("tr");
    row.innerHTML = `<td>${s.company} <small>(${s.id})</small></td>
      <td>${scopeName}</td>
      <td>${s.label_source}</td>
      <td class="num">${truth.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
      <td class="num">${pred.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
      <td class="num">${ratio.toFixed(2)}×</td>
      <td class="num">${eu.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
      <td class="num">${reductionPct >= 0 ? "−" : "+"}${Math.abs(reductionPct).toFixed(0)}%</td>`;
    body.appendChild(row);
  }
  status(`✓ wrote test predictions (${test.length} rows)`);
  $("train-btn").disabled = false;
}

// --- boot ---------------------------------------------------------------
(async () => {
  if (!(await initGPU())) return;
  await loadShaders();
  await loadBench();
  $("train-btn").disabled = false;
  $("train-btn").addEventListener("click", () => { train().catch(e => status("ERROR: " + (e && e.message ? e.message : e))); });
  $("reset-btn").addEventListener("click", () => { lossHistory.train.length = 0; lossHistory.val.length = 0; drawLoss(); $("status").textContent = "reset."; $("train-loss").innerHTML = "— <small>MSE on log-CO₂</small>"; $("val-mae").textContent = "—"; $("step").textContent = "0 / 0"; $("preds-body").innerHTML = ""; });
})();
