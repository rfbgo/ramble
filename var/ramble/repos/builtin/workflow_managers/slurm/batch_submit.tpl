#!/bin/bash
{batch_submit_cmd} | tee >(awk '{print $NF}' > {experiment_run_dir}/.slurm_job)
