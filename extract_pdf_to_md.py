import pdfplumber
import re

PDF_PATH = "La Station Entreprise (2).pdf"
MD_PATH = "la_station.md"

def clean_text(text):
    # Nettoyage léger : conserver les doubles sauts de ligne, éviter les espaces multiples
    text = re.sub(r" +", " ", text)
    return text.strip()

def table_to_markdown(table):
    # Convertit une table (liste de listes) en Markdown
    md = []
    if not table or not any(table):
        return ""
    header = table[0]
    md.append("| " + " | ".join(header) + " |")
    md.append("|" + "---|" * len(header))
    for row in table[1:]:
        md.append("| " + " | ".join(row) + " |")
    return "\n".join(md)

def pdf_to_markdown(pdf_path, md_path):
    with pdfplumber.open(pdf_path) as pdf:
        md_lines = []
        for page in pdf.pages:
            # Extraction des tableaux
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    md_lines.append(table_to_markdown(table))
                    md_lines.append("")
            # Extraction du texte avec tolérance fine
            text = page.extract_text(x_tolerance=1, y_tolerance=1, layout=True)
            if text:
                # On conserve les sauts de ligne et l'indentation
                lines = text.split("\n")
                for line in lines:
                    if not line.strip():
                        md_lines.append("")
                        continue
                    # Titres détectés par majuscules isolées
                    if line.isupper() and len(line.split()) < 10:
                        md_lines.append(f"# {line.strip()}")
                    else:
                        md_lines.append(line.rstrip())
                md_lines.append("")  # Saut de ligne entre pages
    md_text = clean_text("\n".join(md_lines))
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"✅ Extraction terminée. Markdown sauvegardé dans {md_path}")

if __name__ == "__main__":
    pdf_to_markdown(PDF_PATH, MD_PATH) 