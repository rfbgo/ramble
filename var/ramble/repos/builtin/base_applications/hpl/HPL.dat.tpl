    HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
{output_file} # output file name (if any)
{device_out} # (FORTRAN) device out (6=stdout,7=stderr,file)
{N-Ns} # Number of problem sizes (N)
{Ns} # Problem sizes {used_percent_comment}
{N-NBs} # Number of block sizes (NBs)
{NBs} # Block Sizes
{PMAP} # PMAP process mapping (0=Row-Major, 1=Column-Major)
{N-Grids} # Number of grids, process grids (P * Q)
{Ps} # Ps, Dimension 1 parallelization
{Qs} # Qs, Dimension 2 parallelization
{threshold} # Threshold
{NPFACTs} # Number of PFACTs, panel fact
{PFACTs} # PFACT values (0=Left, 1=Crout, 2=Right)
{N-NBMINs} # Number of NBMINs, recursive stopping criteria
{NBMINs} # NBMINs (>= 1)
{N-NDIVs} # Number of NDIVs, panels in recursion
{NDIVs}  # NDIVs
{N-RFACTs} # Number of RFACTs, recursive panel fact.
{RFACTs} # RFACTs (0=Left, 1=Crout, 2=Right)
{N-BCASTs} # Number of BCASTs, broadcast
{BCASTs} # BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM,6=MKL BPUSH,7=AMD Hybrid Panel)
{N-DEPTHs} # Number of DEPTHs, lookahead depth
{DEPTHs} # DEPTHs (>=0)
{SWAP} # SWAP (0=bin-exch, 1=long, 2=mix)
{swapping_threshold} # Swapping threshold
{L1} # L1 in (0=transposed, 1=no-transposed) form
{U} # U in (0=transposed, 1=no-transposed) form
{Equilibration} # Equilibration (0=no, 1=yes)
{mem_alignment} # Memory alignment in double (> 0)
##### This line (no. 32) is ignored (it serves as a separator). ######
