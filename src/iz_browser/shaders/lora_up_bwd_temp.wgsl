// LoRA UP BACKWARD — dL/d(temp).
//
// Forward was: y[m] += scale * sum_r temp[r] * B[m, r]
// So:          dtemp[r] = scale * sum_m dY[m] * B[m, r]
//
// This gradient is NOT additive — it's assigned fresh because `temp` is
// recomputed for every sample during forward and only lives in GPU scratch.
//
// One workgroup per r. 64 threads parallel-reduce across M.
//
// Bindings:
//   @binding(0): dtemp  array<f16>  (read_write) — [RANK] output
//   @binding(1): dY     array<f16>  (read)       — [M]   upstream gradient
//   @binding(2): B      array<f16>  (read)       — [M, RANK] LoRA up weights
//   @binding(3): args   uniform     — { RANK, M, scale, _ }

enable f16;

@group(0) @binding(0) var<storage, read_write> dtemp_buf : array<f16>;
@group(0) @binding(1) var<storage, read> dY_buf : array<f16>;
@group(0) @binding(2) var<storage, read> B_buf : array<f16>;

struct Args {
  RANK: u32,
  M:    u32,
  scale: f32,
  _pad: u32,
}
@group(0) @binding(3) var<uniform> args : Args;

var<workgroup> red_buf : array<f32, 64>;

@compute @workgroup_size(64, 1, 1)
fn lora_up_bwd_temp(
  @builtin(workgroup_id) blockIdx : vec3<u32>,
  @builtin(local_invocation_id) threadIdx : vec3<u32>
) {
  let r : u32 = blockIdx.x;
  if (r >= args.RANK) { return; }

  let RANK : u32 = args.RANK;
  let M : u32 = args.M;
  let tid : u32 = threadIdx.x;

  var acc : f32 = 0.0;
  var m : u32 = tid;
  loop {
    if (m >= M) { break; }
    acc = acc + f32(dY_buf[m]) * f32(B_buf[m * RANK + r]);
    m = m + 64u;
  }

  red_buf[tid] = acc;
  workgroupBarrier();

  if (tid < 32u) { red_buf[tid] = red_buf[tid] + red_buf[tid + 32u]; }
  workgroupBarrier();
  if (tid < 16u) { red_buf[tid] = red_buf[tid] + red_buf[tid + 16u]; }
  workgroupBarrier();
  if (tid < 8u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 8u]; }
  workgroupBarrier();
  if (tid < 4u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 4u]; }
  workgroupBarrier();
  if (tid < 2u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 2u]; }
  workgroupBarrier();
  if (tid < 1u)  { red_buf[tid] = red_buf[tid] + red_buf[tid + 1u]; }
  workgroupBarrier();

  if (tid == 0u) {
    dtemp_buf[r] = f16(args.scale * red_buf[0]);
  }
}
