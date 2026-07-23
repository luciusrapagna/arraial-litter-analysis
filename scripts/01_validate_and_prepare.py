from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "planilha_organizada.xlsx"
PROCESSED = ROOT / "data" / "processed" / "marine_litter_tidy.csv"
REPORT = ROOT / "reports" / "data_validation.json"

EXPECTED_SHA256 = "5dca4fb4c2758d9730059c6c8af2b890edae2cd6a6353d6e62e34f60d69294ff"
ID_COLUMNS = ["beach", "season", "transect"]


def english_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text)).strip("_").lower()


COLUMN_MAP = {
    "Praia": "beach",
    "Estacao_ano": "season",
    "Replica": "transect",
    "Plásticos": "plastic",
    "Isopor": "expanded_polystyrene",
    "Borracha": "rubber",
    "Vidro": "glass",
    "Fragmentos": "fragments",
    "Tecidos": "fabric",
    "Madeira": "processed_wood",
    "Não identificados": "unidentified",
    "Cuidado Pessoal": "personal_care",
    "Alumínio": "aluminium",
    "Aerosol": "aerosol",
    "Anel": "rings_caps",
}

VALUE_MAP = {
    "beach": {"Brava": "Praia Brava", "Ilha": "Ilha do Pontal"},
    "season": {
        "Verão": "Summer",
        "Outono": "Autumn",
        "Inverno": "Winter",
        "Primavera": "Spring",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Official workbook not found: {SOURCE}")

    source_hash = sha256(SOURCE)
    if source_hash != EXPECTED_SHA256:
        raise ValueError(
            "The official workbook differs from the validated source. "
            f"Expected {EXPECTED_SHA256}; found {source_hash}."
        )

    workbook = pd.ExcelFile(SOURCE)
    if workbook.sheet_names != ["Sheet1"]:
        raise ValueError(f"Unexpected worksheet structure: {workbook.sheet_names}")

    raw = pd.read_excel(SOURCE, sheet_name="Sheet1")
    missing_columns = sorted(set(COLUMN_MAP) - set(raw.columns))
    extra_columns = sorted(set(raw.columns) - set(COLUMN_MAP))
    if missing_columns or extra_columns:
        raise ValueError(
            f"Unexpected columns. Missing={missing_columns}; extra={extra_columns}"
        )

    data = raw.rename(columns=COLUMN_MAP).copy()
    for column, mapping in VALUE_MAP.items():
        unexpected = sorted(set(data[column].dropna()) - set(mapping))
        if unexpected:
            raise ValueError(f"Unexpected {column} labels: {unexpected}")
        data[column] = data[column].map(mapping)

    item_columns = [column for column in data.columns if column not in ID_COLUMNS]
    for column in item_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")

    duplicate_keys = int(data.duplicated(ID_COLUMNS).sum())
    missing_values = {key: int(value) for key, value in data.isna().sum().items()}
    negative_cells = int((data[item_columns] < 0).sum().sum())
    non_integer_cells = int(
        ((data[item_columns] % 1 != 0) & data[item_columns].notna()).sum().sum()
    )

    expected_groups = pd.MultiIndex.from_product(
        [["Praia Brava", "Ilha do Pontal"],
         ["Summer", "Autumn", "Winter", "Spring"],
         [1, 2, 3]],
        names=ID_COLUMNS,
    )
    observed_groups = pd.MultiIndex.from_frame(data[ID_COLUMNS])
    missing_groups = [list(value) for value in expected_groups.difference(observed_groups)]
    unexpected_groups = [
        list(value) for value in observed_groups.difference(expected_groups)
    ]

    data["total_items"] = data[item_columns].sum(axis=1)
    data = data.sort_values(ID_COLUMNS, kind="stable").reset_index(drop=True)

    checks = {
        "source_file": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": source_hash,
        "worksheet": "Sheet1",
        "rows": int(len(data)),
        "columns_before_total": int(len(raw.columns)),
        "duplicate_sampling_keys": duplicate_keys,
        "missing_values": missing_values,
        "negative_item_cells": negative_cells,
        "non_integer_item_cells": non_integer_cells,
        "missing_expected_groups": missing_groups,
        "unexpected_groups": unexpected_groups,
        "zero_total_transects": int((data["total_items"] == 0).sum()),
        "totals_by_beach": {
            key: int(value)
            for key, value in data.groupby("beach")["total_items"].sum().items()
        },
        "totals_by_beach_and_season": {
            f"{beach} | {season}": int(value)
            for (beach, season), value
            in data.groupby(["beach", "season"])["total_items"].sum().items()
        },
    }

    failed = (
        duplicate_keys
        or any(missing_values.values())
        or negative_cells
        or non_integer_cells
        or missing_groups
        or unexpected_groups
    )
    checks["validation_status"] = "failed" if failed else "passed"

    PROCESSED.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(PROCESSED, index=False, encoding="utf-8")
    REPORT.write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit("Data validation failed. Review reports/data_validation.json.")


if __name__ == "__main__":
    main()
