// ADAM UPDATE — in-place on an fp16 LoRA parameter buffer.
//
// For each element p:
//   m_t  = beta1 * m_{t-1} + (1 - beta1) * g
//   v_t  = beta2 * v_{t-1} + (1 - beta2) * g²
//   m̂   = m_t / (1 - beta1^t)
//   v̂   = v_t / (1 - beta2^t)
//   p   -= lr * m̂ / (sqrt(v̂) + eps)
//
// Master weights (params) stored as f16 to keep the adapter file tight. m and
// v kept in f32 to avoid update-noise accumulation over many steps. Gradients
// arrive in f16 from the lora_bwd shaders; we upconvert inside.
//
// Bindings:
//   @binding(0): params  array<f16>  (read_write) — P
//   @binding(1): grads   array<f16>  (read)       — dP
//   @binding(2): m_buf   array<f32>  (read_write) — first moment
//   @binding(3): v_buf   array<f32>  (read_write) — second moment
//   @binding(4): args    uniform      — { N, lr, beta1, beta2, eps, bc1, bc2, _ }
//     where bc1 = 1 - beta1^t and bc2 = 1 - beta2^t (bias-correction denominators)

enable f16;

@group(0) @binding(0) var<storage, read_write> params : array<f16>;
@group(0) @binding(1) var<storage, read> grads : array<f16>;
@group(0) @binding(2) var<storage, read_write> m_buf : array<f32>;
@group(0) @binding(3) var<storage, read_write> v_buf : array<f32>;

struct Args {
  N: u32,
  _pad0: u32,
  lr: f32,
  beta1: f32,
  beta2: f32,
  eps: f32,
  bc1: f32,
  bc2: f32,
}
@group(0) @binding(4) var<uniform> args : Args;

@compute @workgroup_size(64, 1, 1)
fn adam_lora(
  @builtin(global_invocation_id) gid : vec3<u32>
) {
  let i : u32 = gid.x;
  if (i >= args.N) { return; }

  let g : f32 = f32(grads[i]);
  let m_prev : f32 = m_buf[i];
  let v_prev : f32 = v_buf[i];

  let m_new : f32 = args.beta1 * m_prev + (1.0 - args.beta1) * g;
  let v_new : f32 = args.beta2 * v_prev + (1.0 - args.beta2) * g * g;

  m_buf[i] = m_new;
  v_buf[i] = v_new;

  let m_hat : f32 = m_new / args.bc1;
  let v_hat : f32 = v_new / args.bc2;

  let p_prev : f32 = f32(params[i]);
  let p_new  : f32 = p_prev - args.lr * m_hat / (sqrt(v_hat) + args.eps);
  params[i] = f16(p_new);
}
