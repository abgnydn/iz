// LoRA DOWN BACKWARD — dL/dx (adapter's contribution).
//
// Forward was: temp[r] = sum_k input[k] * A[r, k]
// So:          dX[k] = sum_r dtemp[r] * A[r, k]
//
// This gradient is the LoRA's contribution to dL/dx and must be ADDED
// into the dL/dx already accumulated from the base matmul's backward.
// (Forward was additive: y = base @ x + alpha/r * B @ A @ x, so backward
// through x is also additive.)
//
// One thread = one output k. workgroup_size(64), dispatch ceil(K/64).
//
// Bindings:
//   @binding(0): dX     array<f16> (read_write) — [K] accumulator (base dX already there)
//   @binding(1): dtemp  array<f16> (read)       — [RANK] upstream
//   @binding(2): A      array<f16> (read)       — [RANK, K] LoRA down weights
//   @binding(3): args   uniform                 — { K, RANK }

enable f16;

@group(0) @binding(0) var<storage, read_write> dX_buf : array<f16>;
@group(0) @binding(1) var<storage, read> dtemp_buf : array<f16>;
@group(0) @binding(2) var<storage, read> A_buf : array<f16>;

struct Args {
  K: u32,
  RANK: u32,
}
@group(0) @binding(3) var<uniform> args : Args;

@compute @workgroup_size(64, 1, 1)
fn lora_down_bwd_x(
  @builtin(global_invocation_id) gid : vec3<u32>
) {
  let k : u32 = gid.x;
  if (k >= args.K) { return; }

  let K : u32 = args.K;
  let RANK : u32 = args.RANK;

  var acc : f32 = 0.0;
  for (var r : u32 = 0u; r < RANK; r = r + 1u) {
    acc = acc + f32(dtemp_buf[r]) * f32(A_buf[r * K + k]);
  }
  let prev : f32 = f32(dX_buf[k]);
  dX_buf[k] = f16(prev + acc);
}
