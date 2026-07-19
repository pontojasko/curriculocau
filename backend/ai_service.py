import os
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_client(model: str) -> AsyncOpenAI:
    if model.startswith("gemini"):
        return AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=os.environ.get("GEMINI_API_KEY", "")
        )
    return AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", "")
    )

SYSTEM_PROMPT = """Você é um especialista em recrutamento de alto nível e sistemas ATS (Applicant Tracking System), além de ser um expert absoluto em LaTeX.
Seu objetivo é otimizar o currículo (escrito em LaTeX) para a vaga de emprego fornecida.

REGRAS ESTRITAS:
1. Adapte as palavras-chave do currículo para estarem alinhadas com a vaga.
2. NUNCA quebre a formatação, estrutura ou pacotes do documento LaTeX original. O arquivo class (.cls) deve continuar funcionando perfeitamente.
3. Se a vaga pedir tecnologias que o candidato pode razoavelmente conhecer com base no seu perfil, ADICIONE as novas tecnologias de forma natural e honesta.
   - REGRA DE INTEGRIDADE HISTÓRICA E TECNOLÓGICA: NUNCA altere, substitua ou falsifique as tecnologias principais (linguagens, frameworks, bancos de dados) de projetos reais ou experiências profissionais já listados no currículo. Por exemplo, se um projeto foi feito em Java e PostgreSQL, NÃO mude para Node.js ou qualquer outra tecnologia apenas para agradar a vaga. A stack original (linguagens e ferramentas) de cada projeto DEVE permanecer estritamente idêntica e verídica.
   - NUNCA crie cargos, empresas ou experiências profissionais fictícias na seção de EXPERIÊNCIA.
   - NUNCA invente ou crie projetos fictícios na seção de PROJETOS. Todos os projetos listados devem ser os originais do currículo.
   - Adicione as novas linguagens/frameworks apenas na seção de HABILIDADES (com destaque adequado) se o perfil do candidato demonstrar afinidade com elas. Não invente sites, URLs ou conquistas que não existem.
4. NUNCA retorne explicações, conversas ou introduções.
5. Retorne APENAS o código LaTeX atualizado e envolto em um bloco Markdown de código (```latex ... ```).
6. REGRAS CRÍTICAS DE LATEX (ESCAPE DE CARACTERES):
   - O caractere '#' é reservado em LaTeX. Sempre escreva 'C\\#' em vez de 'C#' para evitar erros de compilação.
   - O caractere '%' é reservado. Sempre escreva '\\%' em vez de '%'.
   - O caractere '&' é reservado (exceto em tabulares). Em textos comuns, sempre escreva '\\&'.
   - O caractere '_' é reservado. Sempre escreva '\\_' em textos comuns.
7. CONTROLE DE ESPAÇO (MÁXIMO DE 1 PÁGINA):
   - O currículo resultante DEVE caber em exatamente UMA PÁGINA. Escreva descrições detalhadas e completas das experiências e projetos, mas certifique-se de ser conciso o suficiente para que não ultrapasse o limite de uma página. Se você adicionar novos projetos ou detalhes, resuma outros pontos para manter o equilíbrio de espaço.
   - REGRA DE PRIORIZAÇÃO DE ALTO VALOR (HIGH-SIGNAL): Ao resumir ou condensar itens de EXPERIÊNCIA ou PROJETOS para economizar espaço, ordene-os por complexidade técnica e impacto. NUNCA remova ou simplifique conquistas técnicas complexas (ex: integrações complexas, IA/RAG, automações e scripts avançados). Em vez disso, condense e combine impiedosamente tarefas operacionais de rotina e suporte básico (ex: helpdesk, suporte, consultas SQL simples) em menos bullet points.
8. ADAPTAÇÃO DO OBJETIVO E SENIORIDADE:
   - Adapte o cargo e a senioridade na seção "OBJETIVO" para estarem em total conformidade com o que a vaga exige.
   - Se a vaga for de nível "Pleno", "Sênior", "Mid-level", etc., remova qualquer menção a "Estágio" ou "Júnior" no objetivo e substitua por termos adequados (ex: "Desenvolvedor de Software Backend", "Engenheiro de Software", etc.), alinhando o objetivo ao patamar profissional da vaga de forma natural.
9. PRIVACIDADE E NEUTRALIDADE DA CONVENIÊNCIA: NUNCA mencione ou cite o nome da empresa contratante (a empresa da vaga) em qualquer seção do currículo (como objetivo, resumo, projetos ou habilidades). O currículo otimizado resultante deve ser neutro e não conter o nome da empresa-alvo para a qual o candidato está se candidatando."""

ANALYZE_SYSTEM_PROMPT = """Você é um especialista em análise de vagas de emprego e matching de candidatos. Sua tarefa é analisar a descrição de uma vaga e extrair informações críticas em relação ao currículo do candidato (fornecido em LaTeX) para otimização futura.

Instruções:
Analise a descrição da vaga fornecida em comparação com o currículo do candidato e extraia:
1. Keywords Críticas (10-15 palavras-chave mais importantes)
2. Requisitos Técnicos (Stack principal, anos de exp exigidos, conhecimentos obrigatórios vs desejáveis)
3. Match Score Preliminar (0-100% com justificativa baseada nos requisitos, nível de experiência e perfil do candidato)
4. Gaps Identificados:
   - Palavras-chave ou tecnologias que o candidato não tem ou não mencionou.
   - **MANDATÓRIO - Mismatch de Senioridade**: Verifique se o nível da vaga (ex: Pleno, Sênior, PL/SR) é superior ao objetivo/perfil do currículo atual (ex: se o currículo diz "Estágio" ou "Júnior"). Se houver incompatibilidade, adicione isso explicitamente como um Gap de alta importância ("high") com sugestão de remover termos como "Estágio" ou "Júnior" e alinhar o objetivo ao nível da vaga.
   - Competências faltantes e sugestões acionáveis classificando a importância em "high", "medium", "low".
5. Destaques da Vaga (Responsabilidades principais, diferenciais da empresa/posição)
6. Sugestões de melhorias diretas.

Retorne APENAS um JSON válido seguindo a estrutura abaixo, sem markdown (como ```json ou ```), sem explicações ou qualquer outro texto. O JSON deve estar completo e bem formatado:
{
  "keywords": ["React", "TypeScript"],
  "requirements": {
    "mandatory": ["React"],
    "desirable": ["AWS"]
  },
  "matchScore": 87,
  "matchScoreJustification": "...",
  "gaps": [
    {
      "keyword": "AWS",
      "importance": "high",
      "suggestion": "..."
    }
  ],
  "highlights": {
    "mainResponsibilities": ["..."],
    "differentiators": ["..."]
  },
  "suggestions": ["..."]
}
"""

ERROR_PROMPT = """A geração anterior de LaTeX falhou ao compilar. O erro do pdflatex foi:
{error_log}

Por favor, corrija os erros de compilação no código LaTeX.
ATENÇÃO E REGRAS MANDATÓRIAS DE DESIGN E CONTEÚDO:
1. NÃO descarte as otimizações e novas tecnologias da vaga adicionadas. Mantenha a adequação do currículo à vaga intacta.
2. Certifique-se de escapar corretamente os caracteres especiais (ex: C\\# e não C#).
3. MÁXIMO DE 1 PÁGINA e PRIORIZAÇÃO DE ALTO VALOR (HIGH-SIGNAL): O documento final DEVE caber em exatamente 1 página. Se a compilação anterior estourou o espaço, comprima as descrições de experiências e projetos. Ao fazer isso, ordene os itens por complexidade técnica e impacto: NUNCA remova ou simplifique conquistas complexas (ex: IA/RAG, automações e scripts). Em vez disso, condense e combine impiedosamente as tarefas de suporte rotineiro e helpdesk em menos bullet points.
4. SENIORIDADE DO OBJETIVO: Garanta que a seção OBJETIVO esteja alinhada à senioridade da vaga (remova "Estágio" ou "Júnior" se for uma vaga Pleno ou Sênior, adequando o cargo).
5. Lembre-se: retorne APENAS o código LaTeX atualizado dentro de ```latex ... ```."""

LAYOUT_PROMPT = """A geração anterior de LaTeX compilou com sucesso, mas gerou {page_count} páginas, ultrapassando o limite de exatamente 1 página.

Por favor, otimize e comprima o código LaTeX para caber perfeitamente em exatamente 1 página.
Instruções de compressão:
1. MÁXIMO DE 1 PÁGINA e PRIORIZAÇÃO DE ALTO VALOR (HIGH-SIGNAL): Ao condensar experiências ou projetos, ordene-os por complexidade técnica e impacto: NUNCA remova ou simplifique conquistas complexas (ex: IA/RAG, automações e scripts). Em vez disso, condense e combine impiedosamente as tarefas de suporte rotineiro e helpdesk em menos bullet points.
2. Não descarte as palavras-chave e novas tecnologias adicionadas para a vaga.
3. Garanta que o documento final caiba em exatamente 1 página (evitando páginas em branco ou pequenos transbordamentos).
4. Retorne APENAS o código LaTeX atualizado e envolto em ```latex ... ```."""

def extract_latex(response_text: str) -> str:
    """Extracts latex code from a markdown block if present."""
    match = re.search(r'```(?:latex|tex)?\n(.*?)\n```', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response_text.strip()

async def analyze_job_description(model: str, job_description: str, latex_content: str):
    """
    Analyzes the job description and candidate resume to extract keywords, gaps, score, etc.
    Yields chunks of the JSON response in real-time.
    """
    messages = [
        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Descrição da Vaga:\n{job_description}\n\nCurrículo do Candidato (LaTeX):\n{latex_content}"}
    ]
    
    client = get_client(model)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=2000,
        stream=True
    )
    
    async for chunk in response:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

async def generate_optimized_resume(model: str, job_description: str, latex_content: str, job_analysis: str = None, error_log: str = None):
    """
    Calls NVIDIA AI to optimize the resume with streaming enabled.
    Yields chunks of text in real-time.
    """
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    if job_analysis:
        messages.append({
            "role": "system", 
            "content": f"Use esta análise estruturada do matching da vaga e do currículo para guiar sua otimização do LaTeX. Foque em preencher os Gaps identificados, incluir as Keywords críticas e seguir as sugestões de melhoria:\n{job_analysis}"
        })
    
    if error_log:
        messages.append({"role": "user", "content": f"Vaga original:\n{job_description}\n\nLaTeX original:\n{latex_content}"})
        if error_log.startswith("LAYOUT_WARNING:"):
            page_count = error_log.split(":")[-1].strip()
            messages.append({"role": "assistant", "content": "Entendido. Qual foi o problema de layout?"})
            messages.append({"role": "user", "content": LAYOUT_PROMPT.format(page_count=page_count)})
        else:
            messages.append({"role": "assistant", "content": "Entendido. Qual foi o erro de compilação?"})
            messages.append({"role": "user", "content": ERROR_PROMPT.format(error_log=error_log)})
    else:
        user_message = f"VAGA DE EMPREGO:\n{job_description}\n\nCÓDIGO LATEX DO CURRÍCULO:\n{latex_content}"
        messages.append({"role": "user", "content": user_message})

    client = get_client(model)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=4000,
        stream=True
    )
    
    async for chunk in response:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

EMAIL_SYSTEM_PROMPT = """You are an expert software engineer applying for a job.
Write a concise, persuasive email body for your job application.

INSTRUCTIONS:
1. Match the tone of the job description (professional, startup, etc.).
2. Highlight your key strengths based ONLY on the provided resume summary.
3. Keep it under 150 words. Recruiters are busy.
4. Do not invent skills or experiences.
5. Provide ONLY the email text. No subject line, no markdown blocks, no commentary.

EXAMPLE:
Prezado(a) Recrutador(a),

Gostaria de submeter meu currículo para a vaga de [Cargo]. Tenho ampla experiência em [Habilidade 1] e [Habilidade 2], o que me permite contribuir rapidamente para os objetivos da sua equipe.

Em anexo, envio meu currículo detalhando minha trajetória. Agradeço desde já pelo tempo e consideração.

Atenciosamente,
Heitor"""

async def generate_email_body(model: str, job_description: str, job_analysis: str) -> str:
    """
    Generates a short, persuasive email body using prompt engineering patterns.
    """
    messages = [
        {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
        {"role": "user", "content": f"Vaga:\n{job_description}\n\nMeu Resumo Profissional (Analysis):\n{job_analysis}\n\nGere o corpo do e-mail."}
    ]
    
    client = get_client(model)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=300
    )
    
    content = response.choices[0].message.content
    return content.strip() if content else "Prezado(a),\n\nEm anexo meu currículo para a vaga.\n\nAtenciosamente,"

AUTO_APPLY_PROMPT = """Você é o candidato respondendo a um formulário de vaga de emprego.
Aqui está o seu currículo / perfil base:
{profile}

A vaga fez a seguinte pergunta no formulário:
Pergunta: "{question}"
Tipo de Campo: {input_type}
Opções Disponíveis (se houver): {options}

REGRAS:
1. Responda estritamente com o valor a ser preenchido no formulário. NENHUM texto extra.
2. Se for um número (ex: anos de experiência), retorne APENAS o número. Seja coerente com o perfil (inflando de forma sensata se necessário, ex: de 1 para 2 anos, mas não de 1 para 10).
3. Se for 'select' ou 'radio', você DEVE retornar exatamente uma das opções disponíveis.
4. Se a pergunta for sobre proficiência em idiomas, baseie-se no perfil.
"""

async def answer_application_question(model: str, question: str, input_type: str, profile: str, options: list = None) -> str:
    opts_str = ", ".join(options) if options else "Nenhuma"
    prompt = AUTO_APPLY_PROMPT.format(
        profile=profile,
        question=question,
        input_type=input_type,
        options=opts_str
    )
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        client = get_client(model)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Fallback sensato se a IA falhar
        if options:
            return options[0]
        if input_type == "number":
            return "2"
        return "Sim"
