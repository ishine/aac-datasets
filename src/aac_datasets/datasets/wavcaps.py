#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import os
import os.path as osp
import subprocess
import zipfile

from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple

import tqdm

from huggingface_hub import snapshot_download
from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE
from huggingface_hub.utils.tqdm import (
    disable_progress_bars,
    enable_progress_bars,
    are_progress_bars_disabled,
)
from torch import Tensor
from typing_extensions import TypedDict

from aac_datasets.datasets.base import AACDataset, DatasetCard
from aac_datasets.utils.collate import list_dict_to_dict_list
from aac_datasets.utils.download import safe_rmdir


pylog = logging.getLogger(__name__)


class WavCapsItem(TypedDict):
    # Common attributes
    audio: Tensor
    captions: List[str]
    dataset: str
    fname: str
    index: int
    subset: str
    sr: int
    # WavCaps-specific attributes
    author: Optional[str]  # FSD and SB
    description: Optional[str]  # BBC, FSD and SB only
    duration: float
    download_link: Optional[str]  # BBC, FSD and SB only
    href: Optional[str]  # FSD and SB only
    id: str
    source: str
    tags: List[str]  # FSD only


class WavCapsCard(DatasetCard):
    CAPTIONS_PER_AUDIO: Dict[str, int] = {
        "as": 1,
        "bbc": 1,
        "fsd": 1,
        "sb": 1,
    }
    CITATION: str = r"""
    @article{mei2023WavCaps,
        title        = {Wav{C}aps: A {ChatGPT}-Assisted Weakly-Labelled Audio Captioning Dataset for Audio-Language Multimodal Research},
        author       = {Xinhao Mei and Chutong Meng and Haohe Liu and Qiuqiang Kong and Tom Ko and Chengqi Zhao and Mark D. Plumbley and Yuexian Zou and Wenwu Wang},
        year         = 2023,
        journal      = {arXiv preprint arXiv:2303.17395}
    }
    """
    DEFAULT_REVISION: str = "85a0c21e26fa7696a5a74ce54fada99a9b43c6de"
    DESCRIPTION = "WavCaps: A ChatGPT-Assisted Weakly-Labelled Audio Captioning Dataset for Audio-Language Multimodal Research."
    HOMEPAGE = "https://huggingface.co/datasets/cvssp/WavCaps"
    LANGUAGE: Tuple[str, ...] = ("en",)
    NAME: str = "wavcaps"
    PRETTY_NAME: str = "WavCaps"
    SUBSETS: Tuple[str, ...] = ("as", "bbc", "fsd", "sb")
    SAMPLE_RATE: int = 32_000  # Hz


class WavCaps(AACDataset[WavCapsItem]):
    r"""Unofficial WavCaps dataset code.

    WavCaps Paper : https://arxiv.org/pdf/2303.17395.pdf
    HuggingFace source : https://huggingface.co/datasets/cvssp/WavCaps

    This dataset contains 4 training subsets, extracted from different sources:
    - AudioSet strongly labeled (as)
    - BBC Sound Effects (bbc)
    - FreeSound (fsd)
    - SoundBible (sb)

    .. code-block:: text
        :caption:  Dataset folder tree

        {root}
        └── WavCaps
            ├── Audio
            │   ├── AudioSet_SL
            │   │    └── (108317 flac files, ~64GB)
            │   ├── BBC_Sound_Effects
            │   │    └── (31201 flac files, ~142GB)
            │   ├── FreeSound
            │   │    └── (262300 flac files, ~TODOGB) TODO : verif
            │   └── SoundBible
            │        └── (1232 flac files, ~884MB)
            ├── Zip_files
            │   ├── AudioSet_SL
            │   │    └── (8 zip files, ~76GB)
            │   ├── BBC_Sound_Effects
            │   │    └── (26 zip files, ~562GB)
            │   ├── FreeSound
            │   │    └── (100 zip? files, ~274GB) TODO : verif
            │   └── SoundBible
            │        └── (1 zip? files, ~624GB)
            ├── json_files
            │    ├── AudioSet_SL
            │    │    └── as_final.json
            │    ├── BBC_Sound_Effects
            │    │    └── bbc_final.json
            │    ├── FreeSound
            │    │    ├── fsd_final_2s.json
            │    │    └── fsd_final.json
            │    ├── SoundBible
            │    │    └── sb_final.json
            │    └── blacklist
            │         ├── blacklist_exclude_all_ac.json
            │         ├── blacklist_exclude_test_ac.json
            │         └── blacklist_exclude_ubs8k_esc50_vggsound.json
            ├── .gitattributes
            └── README.md
    """

    # Common globals
    CARD: ClassVar[WavCapsCard] = WavCapsCard()
    FORCE_PREPARE_DATA: ClassVar[bool] = False
    VERIFY_FILES: ClassVar[bool] = False

    # WavCaps-specific globals
    CLEAN_ARCHIVES: ClassVar[bool] = False
    EXPECTED_SIZES: ClassVar[Dict[str, int]] = {
        "AudioSet_SL": 108317,
        "BBC_Sound_Effects": 31201,
        "FreeSound": 262300,
        "SoundBible": 1320,  # note: 1232 according to github+hf, but found 1320 => seems that archive contains more data than in json
    }
    REPO_ID: ClassVar[str] = "cvssp/WavCaps"
    RESUME_DL: ClassVar[bool] = True
    SOURCES: ClassVar[Tuple[str, ...]] = tuple(EXPECTED_SIZES.keys())
    ZIP_PATH: ClassVar[str] = "zip"

    def __init__(
        self,
        root: str = ".",
        subset: str = "as",
        download: bool = False,
        transform: Optional[Callable] = None,
        hf_cache_dir: Optional[str] = None,
        revision: Optional[str] = WavCapsCard.DEFAULT_REVISION,
        verbose: int = 1,
    ) -> None:
        self._hf_cache_dir = hf_cache_dir
        self._revision = revision

        if download:
            _prepare_wavcaps_dataset(
                root,
                subset,
                revision,
                hf_cache_dir,
                WavCaps.RESUME_DL,
                WavCaps.FORCE_PREPARE_DATA,
                WavCaps.VERIFY_FILES,
                WavCaps.CLEAN_ARCHIVES,
                WavCaps.ZIP_PATH,
                verbose,
            )

        raw_data = _load_wavcaps_dataset(root, hf_cache_dir, revision, subset)

        size = len(next(iter(raw_data.values())))
        raw_data["dataset"] = [WavCapsCard.NAME] * size
        raw_data["subset"] = [subset] * size
        raw_data["fpath"] = [
            osp.join(
                _get_audio_subset_dpath(
                    root, hf_cache_dir, revision, raw_data["source"][i]
                ),
                fname,
            )
            for i, fname in enumerate(raw_data["fname"])
        ]
        raw_data["index"] = list(range(size))

        super().__init__(
            raw_data=raw_data,
            transform=transform,
            column_names=WavCapsItem.__required_keys__,
            flat_captions=False,
            sr=WavCapsCard.SAMPLE_RATE,
            verbose=verbose,
        )
        self._root = root
        self._subset = subset
        self._download = download

    # Properties
    @property
    def download(self) -> bool:
        return self._download

    @property
    def root(self) -> str:
        return self._root

    @property
    def sr(self) -> int:
        return self._sr  # type: ignore

    @property
    def subset(self) -> str:
        return self._subset


def _get_wavcaps_dpath(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
) -> str:
    return osp.join(root, "WavCaps")


def _get_json_dpath(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
) -> str:
    return osp.join(_get_wavcaps_dpath(root, hf_cache_dir, revision), "json_files")


def _get_archives_dpath(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
) -> str:
    return osp.join(_get_wavcaps_dpath(root, hf_cache_dir, revision), "Zip_files")


def _get_audio_dpath(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
) -> str:
    return osp.join(_get_wavcaps_dpath(root, hf_cache_dir, revision), "Audio")


def _get_audio_subset_dpath(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
    source: str,
) -> str:
    return osp.join(
        _get_audio_dpath(root, hf_cache_dir, revision), _WAVCAPS_AUDIO_DNAMES[source]
    )


def _is_prepared(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
    subset: str,
) -> bool:
    sources = [source for source in WavCaps.SOURCES if _use_source(source, subset)]
    for source in sources:
        audio_fnames = os.listdir(
            _get_audio_subset_dpath(root, hf_cache_dir, revision, source)
        )
        expected_size = WavCaps.EXPECTED_SIZES[source]
        if expected_size != len(audio_fnames):
            pylog.error(
                f"Invalid number of files for source={source}. (expected {expected_size} but found {len(audio_fnames)} files)"
            )
            return False
    return True


def _use_source(source: str, subset: str) -> bool:
    return any(
        (
            source == "AudioSet_SL" and subset in ("as", "as_bbc_sb"),
            source == "BBC_Sound_Effects" and subset in ("bbc", "as_bbc_sb"),
            source == "FreeSound" and subset in ("fsd",),
            source == "SoundBible" and subset in ("sb", "as_bbc_sb"),
        )
    )


def _load_wavcaps_dataset(
    root: str,
    hf_cache_dir: Optional[str],
    revision: Optional[str],
    subset: str,
) -> Dict[str, List[Any]]:
    json_dpath = _get_json_dpath(root, hf_cache_dir, revision)
    json_paths = [
        ("AudioSet_SL", osp.join(json_dpath, "AudioSet_SL", "as_final.json")),
        (
            "BBC_Sound_Effects",
            osp.join(json_dpath, "BBC_Sound_Effects", "bbc_final.json"),
        ),
        ("FreeSound", osp.join(json_dpath, "FreeSound", "fsd_final.json")),
        ("SoundBible", osp.join(json_dpath, "SoundBible", "sb_final.json")),
    ]
    json_paths = [
        (source, json_path)
        for source, json_path in json_paths
        if _use_source(source, subset)
    ]

    raw_data = {k: [] for k in _WAVCAPS_RAW_COLUMNS + ("source", "fname")}
    for source, json_path in json_paths:
        json_data, size = _load_json(json_path)

        sources = [source] * size
        json_data.pop("audio", None)

        if source == "AudioSet_SL":
            ids = json_data["id"]
            fnames = [id_.replace(".wav", ".flac") for id_ in ids]
            raw_data["fname"] += fnames

        elif source == "BBC_Sound_Effects":
            ids = json_data["id"]
            fnames = [f"{id_}.flac" for id_ in ids]
            raw_data["fname"] += fnames

        elif source == "FreeSound":
            ids = json_data["id"]
            fnames = [f"{id_}.flac" for id_ in ids]
            raw_data["fname"] += fnames

        elif source == "SoundBible":
            ids = json_data["id"]
            fnames = [f"{id_}.flac" for id_ in ids]
            raw_data["fname"] += fnames

        else:
            raise RuntimeError(f"Invalid source={source}.")

        for k in _WAVCAPS_RAW_COLUMNS:
            if k in json_data:
                raw_data[k] += json_data[k]
            elif k in _DEFAULT_VALUES:
                default_val = _DEFAULT_VALUES[k]
                default_values = [default_val] * size
                raw_data[k] += default_values
            elif k in ("audio", "file_name"):
                pass
            else:
                raise RuntimeError(f"Invalid column name {k}. (with source={source})")

        raw_data["source"] += sources

    raw_data.pop("audio")
    raw_data.pop("file_name")
    raw_data["captions"] = raw_data.pop("caption")

    # Convert str -> List[str] for captions to match other datasets captions type
    raw_data["captions"] = [[caption] for caption in raw_data["captions"]]
    # Force floating-point precision for duration
    raw_data["duration"] = list(map(float, raw_data["duration"]))
    return raw_data


def _prepare_wavcaps_dataset(
    root: str,
    subset: str,
    revision: Optional[str],
    hf_cache_dir: Optional[str],
    resume_dl: bool,
    force: bool,
    verify_files: bool,
    clean_archives: bool,
    zip_path: str,
    verbose: int,
) -> None:
    if not _is_prepared(root, hf_cache_dir, revision, subset):
        raise RuntimeError(f"WavCaps is not prepared in root={root}.")

    if hf_cache_dir is None:
        hf_cache_dir = HUGGINGFACE_HUB_CACHE

    # Download files from huggingface
    ign_sources = [
        source for source in WavCaps.SOURCES if not _use_source(source, subset)
    ]
    ign_patterns = [
        pattern
        for source in ign_sources
        for pattern in (f"json_files/{source}/*.json", f"Zip_files/*")  # {source}/
    ]
    if verbose >= 2:
        pylog.debug(f"ign_sources={ign_sources}")
        pylog.debug(f"ign_patterns={ign_patterns}")

    pbar_enabled = are_progress_bars_disabled()
    if pbar_enabled and verbose <= 0:
        disable_progress_bars()

    snapshot_dpath = snapshot_download(
        repo_id=WavCaps.REPO_ID,
        repo_type="dataset",
        revision=revision,
        resume_download=resume_dl,
        local_files_only=not force,
        cache_dir=hf_cache_dir,
        allow_patterns=None,
        ignore_patterns=ign_patterns,
    )

    if pbar_enabled and verbose <= 0:
        enable_progress_bars()

    snapshot_abs_dpath = osp.abspath(snapshot_dpath)
    wavcaps_dpath = _get_wavcaps_dpath(root, hf_cache_dir, revision)
    if verbose >= 2:
        pylog.debug(f"snapshot_dpath={snapshot_dpath}")
        pylog.debug(f"snapshot_absdpath={snapshot_abs_dpath}")
        pylog.debug(f"wavcaps_dpath={wavcaps_dpath}")
    del snapshot_dpath

    # Build symlink to hf cache
    if osp.exists(wavcaps_dpath):
        if not osp.islink(wavcaps_dpath):
            raise RuntimeError("WavCaps root exists but it is not a symlink.")
        link_target_abspath = osp.abspath(osp.realpath(wavcaps_dpath))
        if link_target_abspath != snapshot_abs_dpath:
            pylog.error(
                "Target link is not pointing to current snapshot path. It will be automatically replaced."
            )
            os.remove(wavcaps_dpath)
            os.symlink(snapshot_abs_dpath, wavcaps_dpath, True)
    else:
        os.symlink(snapshot_abs_dpath, wavcaps_dpath, True)

    source_and_splitted = [
        ("AudioSet_SL", True),
        ("BBC_Sound_Effects", True),
        ("FreeSound", True),
        ("SoundBible", False),
    ]
    source_and_splitted = {
        source: is_splitted
        for source, is_splitted in source_and_splitted
        if _use_source(source, subset)
    }

    archives_dpath = _get_archives_dpath(root, hf_cache_dir, revision)
    for source, is_splitted in source_and_splitted.items():
        main_zip_fpath = osp.join(
            archives_dpath, _WAVCAPS_ARCHIVE_DNAMES[source], f"{source}.zip"
        )

        if is_splitted:
            merged_zip_fpath = osp.join(
                archives_dpath, _WAVCAPS_ARCHIVE_DNAMES[source], f"{source}_merged.zip"
            )
        else:
            merged_zip_fpath = main_zip_fpath

        if is_splitted and not osp.isfile(merged_zip_fpath):
            cmd = [
                zip_path,
                "-FF",
                main_zip_fpath,
                "--out",
                merged_zip_fpath,
            ]
            if verbose >= 2:
                pylog.debug(f"Merging ZIP files for {source}...")
                pylog.debug(f"Using command: {' '.join(cmd)}")

            if verbose >= 2:
                stdout = None
                stderr = None
            else:
                stdout = subprocess.DEVNULL
                stderr = subprocess.DEVNULL

            subprocess.check_call(cmd, stdout=stdout, stderr=stderr)

        audio_subset_dpath = _get_audio_subset_dpath(
            root, hf_cache_dir, revision, source
        )
        os.makedirs(audio_subset_dpath, exist_ok=True)

        with zipfile.ZipFile(merged_zip_fpath, "r") as file:
            flac_subnames = [name for name in file.namelist() if name.endswith(".flac")]
            assert len(flac_subnames) > 0
            assert all(
                osp.dirname(name) == osp.dirname(flac_subnames[0])
                for name in flac_subnames
            )

            src_root = osp.join(audio_subset_dpath, osp.dirname(flac_subnames[0]))
            src_fnames_found = (
                dict.fromkeys(name for name in os.listdir(src_root))
                if osp.isdir(src_root)
                else {}
            )
            tgt_fnames_found = dict.fromkeys(
                name for name in os.listdir(audio_subset_dpath)
            )

            missing_subnames = [
                subname
                for subname in flac_subnames
                if osp.basename(subname) not in src_fnames_found
                and osp.basename(subname) not in tgt_fnames_found
            ]
            if verbose >= 2:
                pylog.debug(
                    f"Extracting {len(missing_subnames)}/{len(flac_subnames)} audio files from {merged_zip_fpath}..."
                )
            file.extractall(audio_subset_dpath, missing_subnames)
            if verbose >= 2:
                pylog.debug(f"Extraction done.")

        src_fnames_found = (
            dict.fromkeys(name for name in os.listdir(src_root))
            if osp.isdir(src_root)
            else {}
        )
        src_fpaths_to_move = [
            osp.join(audio_subset_dpath, subname)
            for subname in flac_subnames
            if osp.basename(subname) in src_fnames_found
        ]
        if verbose >= 2:
            pylog.debug(f"Moving {len(src_fpaths_to_move)} files...")
        for src_fpath in tqdm.tqdm(src_fpaths_to_move):
            tgt_fpath = osp.join(audio_subset_dpath, osp.basename(src_fpath))
            os.rename(src_fpath, tgt_fpath)
        if verbose >= 2:
            pylog.debug(f"Move done.")

        if verify_files:
            tgt_fnames_expected = [osp.basename(subname) for subname in flac_subnames]
            tgt_fnames_found = dict.fromkeys(
                fname for fname in os.listdir(audio_subset_dpath)
            )
            if verbose >= 2:
                pylog.debug(f"Checking {len(tgt_fnames_expected)} files...")
            tgt_fnames_invalids = [
                fname for fname in tgt_fnames_expected if fname not in tgt_fnames_found
            ]
            if len(tgt_fnames_invalids) > 0:
                raise FileNotFoundError(
                    f"Found {len(tgt_fnames_invalids)}/{len(tgt_fnames_expected)} invalid files."
                )

        safe_rmdir(audio_subset_dpath, rm_root=False, error_on_non_empty_dir=True)

    if clean_archives:
        used_sources = source_and_splitted.keys()
        for source in used_sources:
            archive_source_dpath = osp.join(
                archives_dpath, _WAVCAPS_ARCHIVE_DNAMES[source]
            )
            archives_names = os.listdir(archive_source_dpath)
            for name in archives_names:
                if not name.endswith(".zip") and ".z" not in name:
                    continue
                fpath = osp.join(archive_source_dpath, name)
                if verbose >= 1:
                    pylog.info(f"Removing archive file {name} for source={source}...")
                os.remove(fpath)


def _load_json(fpath: str) -> Tuple[Dict[str, Any], int]:
    with open(fpath, "r") as file:
        data = json.load(file)
    data = data["data"]
    size = len(data)
    data = list_dict_to_dict_list(data, key_mode="same")
    return data, size


class _WavCapsRawItem(TypedDict):
    # Common values
    caption: str
    duration: float
    id: str
    # Source Specific values
    audio: Optional[str]
    author: Optional[str]
    description: Optional[str]
    download_link: Optional[str]
    file_name: Optional[str]
    href: Optional[str]
    tags: Optional[List[str]]


_DEFAULT_VALUES = {
    "author": "",
    "description": "",
    "download_link": "",
    "href": "",
    "tags": [],
}

_WAVCAPS_RAW_COLUMNS = tuple(
    _WavCapsRawItem.__required_keys__ | _WavCapsRawItem.__optional_keys__
)

_WAVCAPS_AUDIO_DNAMES = {
    # Source name to audio directory name
    "AudioSet_SL": "AudioSet_SL",
    "BBC_Sound_Effects": "BBC_Sound_Effects",
    "FreeSound": "FreeSound",
    "SoundBible": "SoundBible",
}

_WAVCAPS_ARCHIVE_DNAMES = {
    # Source name to audio directory name
    "AudioSet_SL": "AudioSet_SL",
    "BBC_Sound_Effects": "BBC_Sound_Effects",
    "FreeSound": "FreeSound",
    "SoundBible": "SoundBible",
}
