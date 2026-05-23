from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Tuple

FORMAT_VERSION = 1


@dataclass
class ModifiedResult:
    item: "Item"
    old_hash: str
    new_hash: str
    new_size: str


@dataclass
class RenameResult:
    item: "Item"
    new_name: str
    new_destino: str
    new_hash: str
    new_size: str


@dataclass
class DuplicateGroup:
    hash_value: str
    paths: List[Path]


@dataclass
class ScanReport:
    new_items: List["Item"]
    missing_items: List["Item"]
    modified_items: List[ModifiedResult]
    renamed_items: List[RenameResult]
    matched_items: List["Item"]
    excluded_in_catalog: List["Item"]
    excluded_on_disk: int
    duplicates: List[DuplicateGroup]

    @property
    def total_changes(self) -> int:
        return (len(self.new_items) + len(self.missing_items) +
                len(self.modified_items) + len(self.renamed_items))

    @property
    def summary(self) -> str:
        parts = []
        if self.new_items:
            parts.append(f"+{len(self.new_items)} nuevos")
        if self.missing_items:
            parts.append(f"-{len(self.missing_items)} faltantes")
        if self.modified_items:
            parts.append(f"~{len(self.modified_items)} modificados")
        if self.renamed_items:
            parts.append(f"~{len(self.renamed_items)} renombrados")
        if self.excluded_in_catalog:
            parts.append(f"⚠{len(self.excluded_in_catalog)} excluidos")
        if self.matched_items:
            parts.append(f"✓{len(self.matched_items)} coincidentes")
        if self.duplicates:
            parts.append(f"📋{len(self.duplicates)} duplicados")
        return " | ".join(parts) if parts else "Sin cambios"


@dataclass
class Item:
    archivo_hash: str = ""
    juego: str = "Aquelarre"
    tipo: str = "otro"
    idioma: str = "es"
    nombre_legible: str = ""
    escaneado: bool = False
    confianza: str = "media"
    edicion: str = "indeterminada"
    destino: str = ""
    descripcion: str = ""
    justificacion: str = ""
    portada: str = ""
    peso: str = ""
    oculto: bool = False
    contenido: Optional[dict] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        return cls(
            archivo_hash=d.get("archivo_hash", ""),
            juego=d.get("juego", "Aquelarre"),
            tipo=d.get("tipo", "otro"),
            idioma=d.get("idioma", "es"),
            nombre_legible=d.get("nombre_legible", ""),
            escaneado=d.get("escaneado", False),
            confianza=d.get("confianza", "media"),
            edicion=d.get("edicion", "indeterminada"),
            destino=d.get("destino", ""),
            descripcion=d.get("descripcion", ""),
            justificacion=d.get("justificacion", ""),
            portada=d.get("portada", ""),
            peso=d.get("peso", ""),
            oculto=d.get("oculto", False),
            contenido=d.get("contenido"),
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["contenido"] is None:
            del d["contenido"]
        if not d["oculto"]:
            del d["oculto"]
        return d

    def display_name(self) -> str:
        return self.nombre_legible or "(sin nombre)"

    def has_portada(self) -> bool:
        return bool(self.portada)

    def portada_filename(self, ext: str = ".jpg") -> str:
        name = Path(self.nombre_legible).stem
        return f"[portada]_{name}{ext}"
