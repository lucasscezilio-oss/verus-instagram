# Aviso no WhatsApp

Quando o robô publica no Instagram, ele te manda uma mensagem no WhatsApp. E se a
publicação **falhar**, ele também avisa. Esse segundo caso é o que realmente importa:
falha aqui é silenciosa, ninguém é notificado por padrão e você só descobriria dias
depois, olhando o perfil.

Enquanto os dois segredos abaixo não existirem, **nada muda**: o robô publica igual e
apenas não avisa. Nada quebra por falta de configuração.

## Por que não é a API oficial da Meta

A WhatsApp Business API exige um portfólio empresarial aprovado, um número dedicado e
modelos de mensagem aprovados pela Meta para mandar mensagem fora da janela de 24 horas.
Esse onboarding já foi tentado neste projeto em julho de 2026 e travou com erro.

Para um aviso operacional que só você recebe, e que não carrega dado de cliente nem
valor de negociação, o CallMeBot resolve em dois minutos. Ele é um serviço de terceiros,
gratuito e sem garantia de disponibilidade. Se um dia sair do ar, você deixa de receber
o aviso, mas **a publicação continua funcionando**, porque o código trata o aviso como
acessório e engole qualquer erro dele.

Se em algum momento o portfólio empresarial for aprovado, dá para trocar só a função
`avisar()` do `publicar.py` pela chamada oficial. O resto do sistema não muda.

## Como ligar (dois minutos, e só você pode fazer)

**1. Pegar a chave do CallMeBot**

- Salve o número **+34 621 331 709** nos seus contatos, com qualquer nome.
- Mande para ele, pelo WhatsApp, exatamente esta mensagem:
  `I allow callmebot to send me messages`
- Ele responde com uma **apikey**. Anote.

**2. Cadastrar os dois segredos no GitHub**

No repositório, vá em **Settings → Secrets and variables → Actions → New repository secret**
e crie os dois:

| Nome | Valor |
|---|---|
| `WHATSAPP_PHONE` | seu número com código do país, sem espaços. Ex: `+5562999446007` |
| `WHATSAPP_APIKEY` | a apikey que o bot respondeu |

**Faça isso você mesmo.** Chave e telefone não passam por mim e não devem ser colados em
conversa nem commitados no repositório. O GitHub guarda os dois criptografados e eles
nunca aparecem no log da execução.

**3. Testar sem esperar o próximo post**

Na aba **Actions**, abra o workflow "Publicar no Instagram" e clique em **Run workflow**.
Se não houver nada pendente na agenda, ele encerra sem publicar e sem avisar, o que já
confirma que o workflow está de pé. O aviso real chega no próximo post que sair.

## O que a mensagem traz

**Quando publica:**

```
Publicado no Instagram agora.

raiox-ed01-2026-08-31
carrossel de 8 imagem(ns), agendado para 12:00

"Goiânia tem o metro quadrado mais barato entre as grandes capitais..."

instagram.com/lucasscez
```

**Quando falha:**

```
FALHOU a publicacao no Instagram em 14/09 15:07 UTC.
A causa mais comum e o token do Instagram ter vencido.
Ver: https://github.com/.../actions/runs/123456789
```

O link vai direto para o log da execução, onde aparece o erro real.

## Detalhe do horário

O agendador do GitHub atrasa de 50 minutos a 1 hora. Um post marcado para as 12:00 sai,
na prática, entre 12:07 e 13:00. O aviso chega no momento da publicação de verdade, não
no horário da agenda. Isso é normal e não é falha.
