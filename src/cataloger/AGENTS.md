# Rules: The Cataloger & Binary Metadata (`src/cataloger/`)

Regras e padrões obrigatórios para o módulo de catalogação e injeção IPTC/EXIF:

1. **Gravação Binária Dupla**:
   - Todo arquivo processado deve receber metadados binários via `iptcinfo3` (IPTC Core) E `piexif` (EXIF IFD0).
   - Conversão de PNG para JPG em alta qualidade (qualidade 98) com preservação de resolução nativa.
2. **Conformidade Estrita com Políticas de IA de Microstock**:
   - `IPTC Caption` / `EXIF ImageDescription`: Deve começar obrigatoriamente com o prefixo `"Generative AI illustration. "` seguido pela descrição completa da cena.
   - `IPTC ObjectName` / `EXIF XPTitle`: Título comercial conciso (< 200 caracteres), sem palavras truncadas ou dangling prepositions (`on`, `with`, `in`, etc.).
   - `IPTC Keywords` / `EXIF XPKeywords`: Exatamente **50 tags** ordenadas por relevância, com presença obrigatória de `["ai generated", "generative ai", "digital art", "illustration"]`.
3. **Higienização de Nomes de Arquivo (`sanitize_filename`)**:
   - Remover prefixos como `generative-ai-image-of-`.
   - Limitar tamanho máximo a 75 caracteres.
   - Nunca deixar preposições ou stopwords no final do nome do arquivo (ex: `...-on-a.jpg`).
4. **Sincronização com CSV**:
   - Além da injeção física no arquivo JPG, atualize sempre `data/processed/adobe_stock_upload.csv` com as colunas esperadas pelo portal Adobe Stock Contributor.
