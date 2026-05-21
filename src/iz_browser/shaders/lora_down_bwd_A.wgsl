// LoRA DOWN BACKWARD — dA accumulation.
//
// Forward was: temp[r] = sum_k input[k] * A[r, k]
// So:          dA[r, k] += dtemp[r] * input[k]
//
// Accumulates into dA (ADD). One thread = one (r, k) pair.
// Dispatch grid: (ceil(K/64), RANK). Each wg of 64 threads covers 64 k's
// for one r.
//
// Bindings:
//   @binding(0): dA      array<f16> (read_write) — [RANK, K] accumulator
//   @binding(1): dtemp   array<f16> (read)       — [RANK] upstream
//   @binding(2): input   array<f16> (read)       — [K] cached forward x
//   @binding(3): args    uniform                 — { K, RANK }

enable f16;

@group(0) @binding(0) var<storage, read_write> dA_buf : array<f16>;
@group(0) @binding(1) var<storage, read> dtemp_buf : array<f16>;
@group(0) @binding(2) var<storage, read> input_buf : array<f16>;

struct Args {
  K: u32,
  RANK: u32,
}
@group(0) @binding(3) var<uniform> args : Args;

@compute @workgroup_size(64, 1, 1)
fn lora_down_bwd_A(
  @builtin(global_invocation_id) gid : vec3<u32>,
  @builtin(workgroup_id) blockIdx : vec3<u32>
) {
  let k : u32 = gid.x;
  let r : u32 = blockIdx.y;
  if (k >= args.K || r >= args.RANK) { return; }

  let dt : f32 = f32(dtemp_buf[r]);
  let x  : f32 = f32(input_buf[k]);
  let idx : u32 = r * args.K + k;
  let prev : f32 = f32(dA_buf[idx]);
  dA_buf[idx] = f16(prev + dt * x);
}
