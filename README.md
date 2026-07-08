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

1. Dê **duplo clique em `instalar.bat`**. Ele detecta se Python e ffmpeg já
   estão instalados e, se não estiverem, instala os dois automaticamente
   via `winget` (recurso nativo do Windows 10/11), além de instalar as
   bibliotecas Python do projeto.
   - Se o Python precisar ser instalado do zero, o script vai pedir para
     você rodar `instalar.bat` **uma segunda vez** depois (o Windows precisa
     atualizar o PATH primeiro).
2. Depois de terminar, dê **duplo clique em `iniciar.bat`** sempre que quiser
   abrir o programa.

Envie a pasta inteira (todos os arquivos `.py` + `instalar.bat` + `iniciar.bat`
+ `requirements.txt`) compactada em `.zip` para a outra pessoa — não é
necessário ter Git nem nenhuma ferramenta extra instalada previamente.

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

## Estrutura de arquivos

```
/video-downloader
├── main.py         # Ponto de entrada — inicia a interface gráfica
├── downloader.py   # Wrapper do yt-dlp, fila de downloads e threading
├── ui.py           # Componentes de interface (PySide6)
├── settings.py     # Carregar/salvar config.json
├── utils.py        # Validação de URL, detecção de plataforma, helpers
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
