# Rules: The Distributor & Multi-Agency Upload (`src/uploader/`)

Regras e padrões obrigatórios para o módulo de distribuição SFTP/FTP e backup:

1. **Protocolos por Agência**:
   - **Adobe Stock**: SFTP nativo com `paramiko` via porta 22 (`sftp.contributor.adobestock.com`).
   - **Freepik, Dreamstime, Pond5, Alamy, Vecteezy, 123RF, Ingram**: FTP seguro com `ftplib` (modo passivo obrigatório).
2. **Livro-Razão de Uploads (`upload_history.json`)**:
   - Nunca reenvie um ativo para uma plataforma na qual ele já consta com status `success`, a menos que o parâmetro `--force` seja passado explicitamente.
   - Atualize o histórico atômica e imediatamente após cada transferência bem-sucedida.
3. **Modo Dry-Run Obrigatório para Testes**:
   - Implementações e testes de conexão devem suportar a flag `--dry-run` para validar autenticação e listagem sem transferir binários desnecessariamente.
4. **Google Drive Cloud Sync**:
   - Verificar se `GOOGLE_DRIVE_LOCAL_PATH` está configurado no `.env`.
   - Registrar cada ativo sincronizado em `data/processed/gdrive_backup_history.json`.
