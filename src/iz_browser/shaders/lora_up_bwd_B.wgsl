// LoRA UP BACKWARD — dB accumulation.
//
// Forward was: output[m] += scale * sum_r temp[r] * B[m, r]
// So:         dB[m, r] += scale * dY[m] * temp[r]
//
// Accumulates into dB (ADD, not overwrite) — caller zeros dB at start of a
// gradient-accumulation round.
//
// One thread = one output row m. Inside the thread we loop over RANK=16.
// workgroup_size(64), dispatch ceil(M/64).
//
// Bindings:
//   @binding(0): dB     array<f16>  (read_write) — [M, RANK] accumulator
//   @binding(1): dY     array<f16>  (read)       — [M]  upstream gradient
//   @binding(2): temp   array<f16>  (read)       — [RANK] cached forward intermediate
//   @binding(3): args   uniform     — { RANK, M, scale, _ }

enable f16;

@group(0) @binding(0) var<storage, read_write> dB_buf : array<f16>;
@group(0) @binding(1) var<storage, read> dY_buf : array<f16>;
@group(0) @binding(2) var<storage, read> temp_buf : array<f16>;

struct Args {
  RANK: u32,
  M:    u32,
  scale: f32,
  _pad: u32,
}
@group(0) @binding(3) var<uniform> args : Args;

@compute @workgroup_size(64, 1, 1)
fn lora_up_bwd_B(
  @builtin(global_invocation_id) gid : vec3<u32>
) {
  let m : u32 = gid.x;
  if (m >= args.M) { return; }

  let RANK : u32 = args.RANK;
  let dy : f32 = f32(dY_buf[m]) * args.scale;
  let row_base : u32 = m * RANK;

  for (var r : u32 = 0u; r < RANK; r = r + 1u) {
    let prev : f32 = f32(dB_buf[row_base + r]);
    let add  : f32 = dy * f32(temp_buf[r]);
    dB_buf[row_base + r] = f16(prev + add);
  }
}
