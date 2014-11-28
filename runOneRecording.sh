#!/bin/bash
#$ -q default.q
#$ -pe smp 8
#$ -l s_vmem=8G
#$ -l h_vmem=10G
#$ -m bea
#$ -M georgi.dzhambazov@upf.edu
#$ -e error.out
#$ -o output.out
echo "downloading fresh source code..."
rm -rf AlignmentDuration
git clone https://github.com/georgid/AlignmentDuration.git
rm -rf htkModelParser
git clone https://github.com/georgid/htkModelParser.git

rm -rf HMMDuration
git clone https://github.com/georgid/HMMDuration.git
rm -rf HMM
git clone https://github.com/MTG/HMM.git

rm -rf AlignmentEvaluation
git clone https://github.com/georgid/AlignmentEvaluation.git
rm -rf utilsLyrics
git clone https://github.com/georgid/utilsLyrics.git

module load python/2.7.5
echo "python after loading module: "
which python
source /homedtic/giorgid/env/bin/activate
echo "python after loading vrit env: "
which python
/homedtic/giorgid/env/bin/python AlignmentDuration/run.py   /homedtic/giorgid/turkish-makam-lyrics-2-audio-test-data/  /homedtic/giorgid/ISTANBUL/