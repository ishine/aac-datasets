<div align="center">

# Automated Audio Captioning datasets in Pytorch

<a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/-Python 3.8+-blue?style=for-the-badge&logo=python&logoColor=white"></a>
<a href="https://pytorch.org/get-started/locally/"><img alt="PyTorch" src="https://img.shields.io/badge/-PyTorch 1.10.1-ee4c2c?style=for-the-badge&logo=pytorch&logoColor=white"></a>
<a href="https://black.readthedocs.io/en/stable/"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-black.svg?style=for-the-badge&labelColor=gray"></a>

Automated Audio Captioning datasets source code on **AudioCaps** [1], **Clotho** [2], and **MACS** [3] datasets.

</div>

## Installation
```bash
pip install https://github.com/Labbeti/aac_datasets
```

## Usage example
```python
from aac_datasets import Clotho
clotho = Clotho(root=".", subset="dev", download=True)
audio, captions, *_ = clotho[0]
```

## Datasets stats
Here is the **train** subset statistics for each dataset :

| | AudioCaps | Clotho | MACS |
|:---:|:---:|:---:|:---:|
| Subset(s) | train, val, test | dev, val, eval, test | full |
| Sample rate | 32000 | 44100 | 48000 |
| Audio source | AudioSet (youtube) | Freesound | TAU Urban Acoustic Scenes 2019 |
| Nb audios | 49838 | 3840 | 3930 |
| Total audio duration | 136.6h<sup>1</sup> | 24.0h | 10.9h |
| Audio duration range | 0.5-10s | 15-30s | 10s |
| Nb captions per audio | 1 | 5 | 2-5 |
| Nb captions | 49838 | 19195 | 17275 |
| Total nb words<sup>2</sup> | 402482 | 217362 | 160006 |
| Nb words range<sup>2</sup> | 1-52 | 8-20 | 5-40 |

<sup>1</sup> This duration is estimated on the total duration of 46230/49838 files of 126.7h.

<sup>2</sup> The sentences are cleaned (lowercase+remove punctuation) and tokenized using the spacy tokenizer to count the words.

## Other requirements (AudioCaps only)
External requirements needed to download **AudioCaps** are **ffmpeg** and **youtube-dl**.
These two programs can be download on Ubuntu using `sudo apt install ffmpeg youtube-dl`.

You can also override their paths for AudioCaps:
```python
from aac_datasets import AudioCaps
AudioCaps.FFMPEG_PATH = "/my/path/to/ffmpeg"
AudioCaps.YOUTUBE_DL_PATH = "/my/path/to/youtube_dl"
_ = AudioCaps(root=".", download=True)
```

## References

[1] C. D. Kim, B. Kim, H. Lee, and G. Kim, “Audiocaps: Generating captions for audios in the wild,” in NAACL-HLT, 2019. Available: https://aclanthology.org/N19-1011/

[2] K. Drossos, S. Lipping, and T. Virtanen, “Clotho: An Audio Captioning Dataset,” arXiv:1910.09387 [cs, eess], Oct. 2019, Available: http://arxiv.org/abs/1910.09387

[3] F. Font, A. Mesaros, D. P. W. Ellis, E. Fonseca, M. Fuentes, and B. Elizalde, Proceedings of the 6th Workshop on Detection and Classication of Acoustic Scenes and Events (DCASE 2021). Barcelona, Spain: Music Technology Group - Universitat Pompeu Fabra, Nov. 2021. Available: https://doi.org/10.5281/zenodo.5770113