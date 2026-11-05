	vmovaps %ymm1, %ymm0
	vmovaps %ymm0, %ymm8
	vmovaps %ymm7, %ymm15
	vmovaps %ymm8, %ymm0
	vmovaps %ymm15, %ymm7
	vmovaps %ymm8, %ymm8
	vmovaps %ymm15, %ymm14
	{evex} vmovaps %ymm1, %ymm0
	vmovaps %ymm16, %ymm0
	vmovaps %ymm0, %ymm31
	vmovaps %ymm30, %ymm31
	vmovaps %zmm1, %zmm0
	vmovaps %zmm8, %zmm0
	vmovaps %zmm16, %zmm0
	vmovaps %zmm0, %zmm31
	vmovaps %zmm31, %zmm30
