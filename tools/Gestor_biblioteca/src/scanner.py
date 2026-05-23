import fnmatch
import hashlib
import threading
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from .utils.formatters import format_bytes
from .models import (
    DuplicateGroup,
    Item,
    ModifiedResult,
    RenameResult,
    ScanReport,
)


class Scanner:
    def __init__(
        self,
        library_root: str,
        existing_items: List[Item],
        scan_exclude: Optional[List[str]] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        self.root = Path(library_root)
        self.existing_items = existing_items
        self.scan_exclude = [p.strip() for p in (scan_exclude or []) if p.strip()]
        self._cancel_event = cancel_event

        self.hash_index: dict[str, Item] = {}
        self.name_dest_index: dict[Tuple[str, str], Item] = {}
        for item in existing_items:
            if item.archivo_hash:
                self.hash_index[item.archivo_hash] = item
            key = (item.nombre_legible, item.destino)
            self.name_dest_index[key] = item

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> ScanReport:
        if not self.root.exists():
            raise FileNotFoundError(f"La ruta de biblioteca no existe: {self.root}")

        found_hashes: Set[str] = set()
        found_names: Set[Tuple[str, str]] = set()

        new_items: List[Item] = []
        matched_items: List[Item] = []
        modified_items: List[ModifiedResult] = []
        renamed_items: List[RenameResult] = []
        total_excluded = 0

        disk_hashes: dict[str, List[Path]] = {}

        all_files = sorted(self.root.rglob("*"))
        total = len(all_files)

        for idx, file_path in enumerate(all_files):
            if self._cancel_event and self._cancel_event.is_set():
                return None
            if not file_path.is_file():
                continue
            if file_path.name == "clasificacion.json":
                continue

            rel_path = file_path.relative_to(self.root)

            if self._is_excluded(rel_path, file_path.name):
                total_excluded += 1
                continue

            if progress_callback and idx % 10 == 0:
                progress_callback(f"Escaneando archivos... ({idx}/{total})")

            destino = str(rel_path.parent) + "/" if rel_path.parent != Path(".") else ""
            nombre_legible = file_path.name

            file_hash = _hash_file(file_path)
            peso = _format_size(file_path.stat().st_size)

            disk_hashes.setdefault(file_hash, []).append(file_path)

            item_by_hash = self.hash_index.get(file_hash)
            key = (nombre_legible, destino)
            item_by_name = self.name_dest_index.get(key)

            if item_by_hash:
                found_hashes.add(file_hash)
                if item_by_hash.destino == destino and item_by_hash.nombre_legible == nombre_legible:
                    matched_items.append(item_by_hash)
                else:
                    renamed_items.append(RenameResult(
                        item=item_by_hash,
                        new_name=nombre_legible,
                        new_destino=destino,
                        new_hash=file_hash,
                        new_size=peso,
                    ))
            elif item_by_name:
                found_names.add(key)
                modified_items.append(ModifiedResult(
                    item=item_by_name,
                    old_hash=item_by_name.archivo_hash,
                    new_hash=file_hash,
                    new_size=peso,
                ))
            else:
                new_item = Item(
                    archivo_hash=file_hash,
                    nombre_legible=nombre_legible,
                    destino=destino,
                    peso=peso,
                    escaneado=False,
                )
                new_items.append(new_item)

        missing_items, excluded_in_catalog = self._find_unaccounted(found_hashes, found_names)

        duplicates = self._find_duplicates(disk_hashes, found_hashes)

        return ScanReport(
            new_items=new_items,
            missing_items=missing_items,
            modified_items=modified_items,
            renamed_items=renamed_items,
            matched_items=matched_items,
            excluded_in_catalog=excluded_in_catalog,
            excluded_on_disk=total_excluded,
            duplicates=duplicates,
        )

    def _is_excluded(self, rel_path: Path, filename: str) -> bool:
        if not self.scan_exclude:
            return False
        rel_lower = str(rel_path).lower()
        for pattern in self.scan_exclude:
            pat = pattern.lstrip("./").lower()
            if rel_lower == pat or rel_lower.startswith(pat + "/"):
                return True
            if fnmatch.fnmatch(rel_lower, pat) or fnmatch.fnmatch(filename.lower(), pat):
                return True
        return False

    def _find_unaccounted(
        self, found_hashes: Set[str], found_names: Set[Tuple[str, str]]
    ) -> Tuple[List[Item], List[Item]]:
        missing: List[Item] = []
        excluded: List[Item] = []
        for item in self.existing_items:
            if item.archivo_hash and item.archivo_hash in found_hashes:
                continue
            key = (item.nombre_legible, item.destino)
            if key in found_names:
                continue
            file_path = self.root / item.destino.lstrip("/") / item.nombre_legible
            if file_path.exists():
                excluded.append(item)
            else:
                missing.append(item)
        return missing, excluded

    def _find_duplicates(
        self, disk_hashes: dict[str, List[Path]], found_hashes: Set[str]
    ) -> List[DuplicateGroup]:
        groups: List[DuplicateGroup] = []
        for h, paths in disk_hashes.items():
            if len(paths) > 1 and h not in found_hashes:
                groups.append(DuplicateGroup(hash_value=h, paths=sorted(paths)))
        return groups


def _hash_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _format_size(size_bytes: int) -> str:
    return format_bytes(size_bytes)
