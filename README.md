# 🟥 MasterApp

Aplicativo pessoal de desktop para baixar vídeos do YouTube, Instagram,
Twitter/X, TikTok, Reddit, Facebook e qualquer outra plataforma suportada
pelo [`yt-dlp`](https://github.com/yt-dlp/yt-dlp), com seleção de qualidade
até 4K — além de conversão de mídia local e uma aba de OCR/conversão de
documentos.

## Requisitos

- Windows 10/11
- Python 3.10 ou superior
- [ffmpeg](https://ffmpeg.org/download.html) instalado no sistema (necessário
  para mesclar vídeo+áudio em qualidades acima de 360p, extrair áudio em
  MP3 e para a aba de conversão de mídia local)
- Para a aba **📄 Documentos** (OCR e conversão de documentos): Tesseract
  OCR e, opcionalmente, Poppler e Microsoft Word/LibreOffice — veja a seção
  [Aba "Documentos"](#aba-documentos-ocr-e-conversão-de-documentos) mais
  abaixo. O restante do app funciona normalmente mesmo sem eles.

## Instalação rápida (recomendado para enviar a outra pessoa)

Se você recebeu esta pasta de alguém (ou vai repassá-la), não precisa mexer
em terminal:

1. Dê **duplo clique em `scripts\instalar.bat`**. Ele verifica se Python
   3.10+ está instalado (abrindo a página de download se não estiver),
   instala/atualiza o `pip` e todas as bibliotecas do `requirements.txt`, e
   avisa (com link de download) se `ffmpeg` ou `tesseract` não estiverem no
   `PATH` do sistema.
2. Depois de terminar, dê **duplo clique em `scripts\iniciar.bat`** sempre
   que quiser abrir o programa.

Envie a pasta inteira (`src/`, `scripts/`, `requirements.txt`, `README.md`)
compactada em `.zip` para a outra pessoa — não é necessário ter Git nem
nenhuma ferramenta extra instalada previamente.

### Instalando o ffmpeg/tesseract manualmente

- **ffmpeg**: baixe o build "essentials" em
  https://www.gyan.dev/ffmpeg/builds/ (ou `winget install ffmpeg`), extraia
  o `.zip` e adicione a pasta `bin` ao `PATH` do Windows. Confirme com
  `ffmpeg -version` em um terminal novo. Se preferir não mexer no `PATH`,
  informe o caminho completo do executável em **Configurações → Caminho
  customizado do ffmpeg** dentro do próprio app.
- **tesseract**: veja a seção [Aba "Documentos"](#aba-documentos-ocr-e-conversão-de-documentos)
  mais abaixo.

## Instalação manual (via terminal)

```bash
pip install -r requirements.txt
```

## Executando

```bash
python src/main.py
```

Ou, no Windows, dê duplo clique em `scripts\iniciar.bat`. O app funciona a
partir de qualquer diretório de trabalho — ele resolve seus próprios
caminhos (config, pasta de downloads) relativos à localização do próprio
projeto e à pasta pessoal do usuário, nunca `Program Files`. O
`config.json` fica sempre na raiz do projeto (fora de `src/`), então
sobrevive a futuras atualizações do código.

## Como usar

1. Cole um link de vídeo no campo de texto (pode colar vários links, um por
   linha, para adicionar todos de uma vez).
2. Escolha a qualidade desejada no dropdown (`4K`, `1080p`, `720p`, `480p`,
   `360p`, `Melhor qualidade disponível` ou `Apenas áudio (MP3)`).
3. Clique em **▶ Adicionar** — o vídeo entra na fila e o app busca título e
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
o `yt-dlp` cai automaticamente para a melhor qualidade disponível abaixo
disso. Depois que o download termina, o app mostra, ao lado do título, a
qualidade **realmente** baixada (que pode ser menor do que a selecionada).

### Tema claro/escuro

O ícone ☀/🌙 no canto superior direito do cabeçalho alterna entre os temas
escuro (padrão) e claro instantaneamente, sem precisar reiniciar o app. A
preferência é salva em `config.json` e usada automaticamente na próxima
abertura. O mesmo tema também pode ser escolhido na tela de Configurações.

### Configurações

Acessível pelo botão **⚙ Config** no cabeçalho:

- Pasta de destino (padrão: `~/Videos/Downloads`)
- Qualidade padrão usada ao adicionar novos links
- Número de downloads simultâneos (1 a 3)
- Tema (escuro/claro)
- Usar ffmpeg para mesclar áudio/vídeo (ligado por padrão)
- Salvar thumbnail junto com o vídeo
- Salvar metadados do vídeo (`.info.json`)
- Caminho customizado do ffmpeg (caso não esteja no `PATH`)

Tudo é salvo automaticamente em `config.json`, na raiz do projeto.

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

1. Clique em **+ Adicionar arquivos** (podem ser de formatos diferentes,
   desde que compartilhem pelo menos um formato de destino em comum — "PDF"
   está sempre disponível como destino).
2. Escolha o formato de destino no dropdown — as opções mudam de acordo com
   o(s) arquivo(s) selecionado(s). Arquivos que não suportam o destino
   escolhido ficam marcados "Não suportado" e são pulados automaticamente.
3. Escolha a pasta de saída e clique em **▶ Converter**.
4. Cada arquivo mostra seu status (`Aguardando`, `Convertendo...`,
   `Concluído ✓`, `Erro ✗`) e o rodapé mostra o progresso geral
   ("2 de 3 arquivos convertidos"). Use o **[✕]** de cada linha para
   remover um arquivo específico da fila, ou **🗑 Remover todos** para
   limpar tudo de uma vez.
5. Ao terminar, use **📂 Abrir pasta de saída** para ver o resultado no
   Explorer.

Conversões suportadas:

| De | Para |
|---|---|
| JPG / PNG / BMP / WEBP / TIFF | PDF, ou qualquer outro formato de imagem da lista |
| PDF | JPG, PNG (uma imagem por página), DOCX, TXT |
| DOCX | PDF, TXT |
| TXT | PDF, DOCX |
| Qualquer mistura dos formatos acima | Um único PDF mesclado (marque "Mesclar tudo em um único PDF" quando o destino for PDF) — arraste as linhas para reordenar as páginas antes de converter, e PDFs protegidos por senha são suportados (o app pede a senha de cada um) |

Saída padrão: `~/Documents/Convertidos`.

### Dependências extras desta aba

O `scripts\instalar.bat` verifica `tesseract` no PATH (veja acima). As
instruções abaixo são para quem prefere instalar manualmente, ou precisa de
Poppler/LibreOffice (não checados pelo instalador). Além do `ffmpeg` já
usado pelo resto do app, a aba Documentos precisa de:

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
  converter PDF → imagem, mesclar PDF):
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
/MasterApp
├── src/                      # todo o código-fonte Python
│   ├── main.py               # Ponto de entrada — inicia a interface gráfica
│   ├── ui.py                 # Componentes de interface (PySide6)
│   ├── theme.py              # Sistema de tema centralizado (dark/light, apply_theme)
│   ├── downloader.py         # Wrapper do yt-dlp, fila de downloads e threading
│   ├── converter.py          # Conversor de mídia local via ffmpeg, fila e threading
│   ├── settings.py           # Carregar/salvar config.json (na raiz do projeto)
│   ├── utils.py              # Validação de URL, detecção de plataforma, helpers
│   └── documentos/           # Aba "Documentos": OCR e conversão de documentos
│       ├── __init__.py
│       ├── ocr_engine.py     # pytesseract / pdf2image + exportar .txt/.docx/.pdf
│       ├── converter.py      # Conversão de imagem/PDF/DOCX/TXT (Pillow, reportlab,
│       │                     # pdf2image, pdf2docx, pdfplumber, docx2pdf, pypdf)
│       ├── workers.py        # QThread workers de OCR e conversão
│       └── tab_documentos.py # Widget da aba (sub-abas Digitalizar/Converter)
├── scripts/                  # scripts executáveis, separados do código-fonte
│   ├── instalar.bat          # Verifica Python/pip, instala dependências, checa ffmpeg/tesseract
│   └── iniciar.bat           # Abre o programa (duplo clique)
├── config.json                # Criado automaticamente na primeira execução
├── requirements.txt
└── README.md
```

## Detalhes técnicos

- **GUI**: PySide6, rodando 100% na thread principal. Nenhum download roda
  na thread da interface — cada item baixa em sua própria `threading.Thread`,
  e o progresso é reportado de volta à interface via sinais Qt
  (thread-safe por padrão).
- **Tema**: centralizado em `theme.py` — uma única `apply_theme()` aplica o
  stylesheet inteiro da aplicação; nenhum widget define estilo inline para
  fins de tema. Linhas de fila (downloads/conversões) mudam a cor da borda
  esquerda dinamicamente via uma propriedade Qt (`status`), não por CSS
  fixo, então o mesmo código funciona em ambos os temas automaticamente.
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
