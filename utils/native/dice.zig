// compile with 
// zig build-lib dice.zig -dynamic -O ReleaseFast

const Rand = @import("std").Random;

inline fn roll(Rng: type, seed: u64, n: u64, d: u64) u128 {
	var rand = Rng.init(seed);
	var rng = rand.random();
	var total: u128 = 0;
	var i: u64 = 0;
	while(i + 8  <= n) : (i += 8) {
		inline for(0..8)|_|{
			total += @as(u128, rng.uintLessThan(u64, d)) + 1;
		}
	}
	while(i < n) : (i += 1) {
		total += @as(u128, rng.uintLessThan(u64, d)) + 1;
	}
	return total;
}

export fn dice(seed: u64, n: u64, d: u64, ol: *u64, ou: *u64) void {
	var res: u128 = undefined;
	if(n < 1_000_000){
		res = roll(Rand.Xoshiro256, seed, n, d);
	}else if(n < 1_000_000_000){
		res = roll(Rand.Sfc64, seed, n, d);
	}else {
		var rand = Rand.Xoshiro256.init(seed);
		var rng = rand.random();
		const fN: f64 = @floatFromInt(n);
		const fD: f64 = @floatFromInt(d);
		const v = rng.floatNorm(f64) * @sqrt(fN * (fD * fD - 1) / 12) + fN * (fD + 1) / 2;
		res = @intFromFloat(@max(v, fN));
	}
	ol.* = @truncate(res);
	ou.* = @truncate(res >> 64);
}
