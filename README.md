# 🎬 Video Downloader

Aplicativo pessoal de desktop para baixar vídeos do YouTube, Instagram,
Twitter/X, TikTok, Reddit, Facebook e qualquer outra plataforma suportada
pelo [`yt-dlp`](https://github.com/yt-dlp/yt-dlp), com seleção de qualidade
até 4K.

## Requisitos

- Windows 10/11
- Python 3.10 ou superior
- [ffmpeg](https://ffmpeg.org/download.html) instalado no sistema (necessário
  para mesclar vídeo+áudio em qualidades acima de 360p e para extrair áudio
  em MP3)
- Para a aba **📄 Documentos** (OCR e conversão de documentos): Tesseract
  OCR e, opcionalmente, Poppler e Microsoft Word/LibreOffice — veja a seção
  [Aba "Documentos"](#aba-documentos-ocr-e-conversão-de-documentos) mais
  abaixo. O restante do app funciona normalmente mesmo sem eles.

### Instalando o ffmpeg no Windows

1. Baixe o build "essentials" em https://www.gyan.dev/ffmpeg/builds/ (ou via
   `winget install ffmpeg` / `choco install ffmpeg`).
2. Extraia o `.zip` e adicione a pasta `bin` ao `PATH` do Windows.
3. Confirme rodando `ffmpeg -version` em um terminal novo.

Se preferir não mexer no `PATH`, informe o caminho completo do executável em
**Configurações → Caminho customizado do ffmpeg** dentro do próprio app.

## Instalação rápida (recomendado para enviar a outra pessoa)

Se você recebeu esta pasta de alguém (ou vai repassá-la), não precisa mexer
em terminal:

1. Dê **duplo clique em `instalar.bat`**. Ele detecta o que já está
   instalado e instala automaticamente o que faltar via `winget` (recurso
   nativo do Windows 10/11): Python, ffmpeg, Tesseract OCR e Poppler — além
   de instalar todas as bibliotecas Python do projeto.
   - Se o Python precisar ser instalado do zero, o script vai pedir para
     você rodar `instalar.bat` **uma segunda vez** depois (o Windows precisa
     atualizar o PATH primeiro).
   - Se ffmpeg ou Poppler forem instalados nessa execução, **reinicie o
     computador** (ou pelo menos saia e entre de novo na sua conta) antes
     de usar o app — o script avisa isso na tela final quando necessário.
   - DOCX → PDF continua precisando do Microsoft Word ou do
     [LibreOffice](https://www.libreoffice.org/download) instalado à parte
     — não é baixado automaticamente por ser um instalador grande.
2. Depois de terminar, dê **duplo clique em `iniciar.bat`** sempre que quiser
   abrir o programa.

Envie a pasta inteira (todos os arquivos `.py` + a pasta `documentos/` +
`instalar.bat` + `iniciar.bat` + `requirements.txt`) compactada em `.zip`
para a outra pessoa — não é necessário ter Git nem nenhuma ferramenta extra
instalada previamente.

### "winget indisponível" mesmo com o winget instalado

Se `instalar.bat` mostrar "AVISO: winget indisponível" mas você sabe que o
winget funciona no seu PC (abra um terminal novo e rode `winget --version`
para confirmar), a causa provável é o **Explorer do Windows** estar rodando
há muito tempo com uma cópia desatualizada do `PATH` em memória — qualquer
`.bat` aberto por duplo clique herda esse `PATH` velho, mesmo que o winget
já esteja instalado e funcionando em terminais abertos depois disso.
Soluções, da mais rápida para a mais garantida:

1. Reinicie o Explorer: Gerenciador de Tarefas → aba Processos → "Explorador
   de Arquivos" → Reiniciar.
2. Ou simplesmente reinicie o computador.
3. Depois, rode `instalar.bat` de novo.

## Instalação manual (via terminal)

```bash
pip install -r requirements.txt
```

## Executando

```bash
python main.py
```

O app funciona a partir de qualquer diretório de trabalho — ele resolve seus
próprios caminhos (config, pasta de downloads) relativos à localização dos
arquivos `.py` e à pasta pessoal do usuário, nunca `Program Files`.

## Como usar

1. Cole um link de vídeo no campo de texto (pode colar vários links, um por
   linha, para adicionar todos de uma vez).
2. Escolha a qualidade desejada no dropdown (`4K`, `1080p`, `720p`, `480p`,
   `360p`, `Melhor qualidade disponível` ou `Apenas áudio (MP3)`).
3. Clique em **Adicionar** — o vídeo entra na fila e o app busca título e
   thumbnail em segundo plano.
4. Clique em **▶ Iniciar tudo** para começar a baixar a fila.
5. Acompanhe progresso, velocidade e ETA de cada item em tempo real.
6. Use **⏸ Pausar** para impedir que novos itens comecem (downloads já em
   andamento são concluídos normalmente — pausar um download HTTP no meio da
   transferência não é algo que o `yt-dlp` suporte de forma segura).
7. Use **✕ Cancelar** em um item para interrompê-lo, ou **↻ Tentar
   novamente** em itens com erro.
8. Use **🗑 Limpar concluídos** para remover da lista os itens já baixados
   ou cancelados.

### Convertendo arquivos locais (aba "🔄 Converter Arquivos")

Além de baixar vídeos, o app também converte arquivos que já estão no seu
PC entre formatos de vídeo, áudio ou imagem:

1. Na aba **🔄 Converter Arquivos**, clique em **🗂 Selecionar arquivo(s)**
   ou arraste um ou mais arquivos para a área pontilhada.
2. O app identifica automaticamente o formato pelo tipo do arquivo (vídeo,
   áudio ou imagem) e sugere um formato de destino diferente no dropdown ao
   lado — troque para qualquer outro formato da mesma categoria antes de
   converter.
3. Clique em **▶ Converter tudo**. O progresso, velocidade e status de cada
   arquivo aparecem em tempo real, igual à fila de downloads.
4. O arquivo convertido é salvo na mesma **pasta de destino** configurada
   para os downloads.

Formatos suportados:

- **Vídeo:** MP4, MKV, AVI, MOV, WEBM, FLV
- **Áudio:** MP3, WAV, AAC, FLAC, OGG, M4A, WMA
- **Imagem:** PNG, JPG/JPEG, WEBP, BMP, GIF, TIFF

A conversão só troca entre formatos da mesma categoria (ex: MP4 → MKV, ou
MP3 → FLAC) — para extrair o áudio de um vídeo baixado, use a opção
`Apenas áudio (MP3)` na aba de Downloads. A conversão usa o mesmo `ffmpeg`
já exigido pelo restante do app.

### Qualidade e fallback automático

Ao selecionar uma qualidade (ex: `1080p Full HD`), o app pede ao `yt-dlp` os
melhores streams de vídeo e áudio disponíveis **até** aquele limite de
altura. Se a plataforma não oferecer essa qualidade para o vídeo em questão,
o `yt-dlp` cai automaticamance para a melhor qualidade disponível abaixo
disso. Depois que o download termina, o app mostra, ao lado do título, a
qualidade **realmente** baixada (que pode ser menor do que a selecionada).

### Configurações

Acessível pelo botão **⚙ Configurações** no topo da janela:

- Pasta de destino (padrão: `~/Videos/Downloads`)
- Qualidade padrão usada ao adicionar novos links
- Número de downloads simultâneos (1 a 3)
- Tema (escuro/claro)
- Usar ffmpeg para mesclar áudio/vídeo (ligado por padrão)
- Salvar thumbnail junto com o vídeo
- Salvar metadados do vídeo (`.info.json`)
- Caminho customizado do ffmpeg (caso não esteja no `PATH`)

Tudo é salvo automaticamente em `config.json`, na mesma pasta dos arquivos
`.py`.

## Aba "📄 Documentos" (OCR e conversão de documentos)

Uma terceira aba, independente das de Downloads, com duas funções que
funcionam 100% offline (nenhuma delas depende de internet):

### 🔍 Digitalizar (OCR)

1. Clique em **📂 Selecionar Arquivo** e escolha uma imagem (`.jpg`, `.png`,
   `.bmp`, `.tiff`, `.webp`) ou um PDF escaneado.
2. Uma prévia do arquivo aparece à esquerda. Escolha o **idioma** do texto
   (Português, Inglês, Espanhol ou Automático).
3. Clique em **🔍 Digitalizar** — o OCR roda em segundo plano (nunca trava a
   interface). PDFs de várias páginas mostram uma barra de progresso
   "Página X de Y"; imagens únicas mostram um indicador de carregamento.
4. O texto extraído aparece **editável** à direita — corrija o que precisar
   antes de salvar.
5. Use **📋 Copiar Texto**, ou salve como **.TXT**, **.DOCX** ou **.PDF**
   (o PDF gerado contém texto real e pesquisável, não uma imagem).

Saída padrão: `~/Documents/Digitalizados` (configurável só editando
`config.json` por enquanto — não há campo na tela de Configurações para
isso ainda).

### 🔄 Converter Formato

1. Clique em **+ Adicionar arquivos** (ou arquivos de formatos diferentes,
   desde que compartilhem pelo menos um formato de destino em comum).
2. Escolha o formato de destino no dropdown — as opções mudam de acordo com
   o(s) arquivo(s) selecionado(s).
3. Escolha a pasta de saída e clique em **▶ Converter**.
4. Cada arquivo mostra seu status (`Aguardando`, `Convertendo...`,
   `Concluído ✓`, `Erro ✗`) e o rodapé mostra o progresso geral
   ("2 de 3 arquivos convertidos").
5. Ao terminar, use **📂 Abrir pasta de saída** para ver o resultado no
   Explorer.

Conversões suportadas:

| De | Para |
|---|---|
| JPG / PNG / BMP / WEBP / TIFF | PDF, ou qualquer outro formato de imagem da lista |
| PDF | JPG, PNG (uma imagem por página), DOCX, TXT |
| DOCX | PDF |
| Várias imagens | Um único PDF mesclado (marque a caixa "Mesclar..." quando aparecer) |

Saída padrão: `~/Documents/Convertidos`.

### Dependências extras desta aba

O `instalar.bat` já instala Tesseract e Poppler automaticamente (veja
[Instalação rápida](#instalação-rápida-recomendado-para-enviar-a-outra-pessoa)
acima). As instruções abaixo são só para quem prefere instalar manualmente.
Além do `ffmpeg` já usado pelo resto do app, a aba Documentos precisa de:

- **Tesseract OCR** (motor de reconhecimento de texto):
  - Windows: baixe o instalador em
    https://github.com/UB-Mannheim/tesseract/wiki
  - Durante a instalação, marque os pacotes de idioma **Português** e
    **Inglês**.
  - Adicione a pasta de instalação ao `PATH` do Windows (normalmente
    `C:\Program Files\Tesseract-OCR`) — ou apenas deixe como está, o app
    detecta esse caminho padrão automaticamente mesmo sem PATH.
  - Se não for encontrado, o app mostra um aviso claro assim que a aba
    Documentos é aberta, explicando como instalar.
- **Poppler** (necessário só para operações com PDF: digitalizar PDF,
  converter PDF → imagem):
  - Windows: baixe em
    https://github.com/oschwartz10612/poppler-windows/releases, extraia o
    `.zip` e adicione a pasta `Library\bin` ao `PATH` do Windows.
  - Sem o poppler, essas operações específicas mostram uma mensagem de erro
    clara em vez de travar o app.
- **DOCX → PDF** precisa do **Microsoft Word** instalado (Windows, usado
  via automação COM) **ou** do **LibreOffice** instalado como alternativa
  (`soffice --headless`). Sem nenhum dos dois, o app mostra um erro claro
  em vez de travar.

## Estrutura de arquivos

```
/video-downloader
├── main.py         # Ponto de entrada — inicia a interface gráfica
├── downloader.py   # Wrapper do yt-dlp, fila de downloads e threading
├── converter.py    # Conversor de mídia local via ffmpeg, fila e threading
├── ui.py           # Componentes de interface (PySide6)
├── settings.py     # Carregar/salvar config.json
├── utils.py        # Validação de URL, detecção de plataforma, helpers
├── documentos/     # Aba "Documentos": OCR e conversão de documentos
│   ├── __init__.py
│   ├── ocr_engine.py     # pytesseract / pdf2image + exportar .txt/.docx/.pdf
│   ├── converter.py      # Conversão de imagem/PDF/DOCX (Pillow, reportlab,
│   │                     # pdf2image, pdf2docx, pdfplumber, docx2pdf)
│   ├── workers.py        # QThread workers de OCR e conversão
│   └── tab_documentos.py # Widget da aba (sub-abas Digitalizar/Converter)
├── config.json     # Criado automaticamente na primeira execução
├── instalar.bat    # Instala Python/ffmpeg/dependências automaticamente
├── iniciar.bat     # Abre o programa (duplo clique)
├── requirements.txt
└── README.md
```

## Detalhes técnicos

- **GUI**: PySide6, rodando 100% na thread principal. Nenhum download roda
  na thread da interface — cada item baixa em sua própria `threading.Thread`,
  e o progresso é reportado de volta à interface via sinais Qt
  (thread-safe por padrão).
- **Engine**: `yt-dlp` é usado via API Python (não subprocess), o que
  permite hooks de progresso em tempo real, seleção fina de formato e
  pós-processamento (merge/conversão) integrados.
- **Retry automático**: até 3 tentativas por item em caso de erro
  transitório (ex: limitação de taxa), com backoff progressivo. Vídeos
  privados/indisponíveis são detectados e marcados como `Indisponível` sem
  consumir tentativas de retry.
- **Mesclagem**: quando a qualidade selecionada exige stream de vídeo e
  áudio separados (comum a partir de 720p/1080p no YouTube), o `yt-dlp`
  usa o ffmpeg para mesclá-los automaticamente em `.mp4`.

## Solução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| "ffmpeg não encontrado" | ffmpeg não está instalado ou não está no PATH | Instale o ffmpeg ou informe o caminho manualmente nas Configurações |
| Item fica "Indisponível" | Vídeo privado, removido ou exige login | Nada a fazer no app — o conteúdo não está acessível publicamente |
| Download trava em 0% | Link inválido ou plataforma não suportada pelo yt-dlp | Verifique a URL; consulte a lista de extratores do yt-dlp |
| Qualidade baixada é menor que a selecionada | A plataforma não oferece aquele stream para este vídeo | Comportamento esperado — o app mostra a qualidade real ao lado do título |

## Aviso

Este aplicativo é destinado a uso pessoal. Respeite os termos de uso das
plataformas e os direitos autorais do conteúdo baixado.
