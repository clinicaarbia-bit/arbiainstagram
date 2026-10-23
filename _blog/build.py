"""Gera o blog da Clínica Arbia a partir de _blog/posts/*.md.

Uso (na pasta site/):  python3 _blog/build.py

Cada post é um .md com cabeçalho (front matter) e corpo:

    ---
    titulo: Vasinhos nas pernas: o que são e como tratar
    slug: vasinhos-nas-pernas
    descricao: Resumo de até ~155 caracteres para o Google.
    area: Angiologia
    especialista: Dra. Vanessa Lins
    data: 2026-10-23
    ---
    Parágrafo de abertura (responde a pergunta principal de forma direta).

    ## Resumo
    - ponto-chave

    ## Uma seção
    Texto com **negrito** e [links](/rota).

    ## Perguntas frequentes
    ### Pergunta?
    Resposta.

"## Resumo" vira o quadro de destaque e "## Perguntas frequentes" vira o FAQ
(também enviado ao Google como FAQPage). Depois de gerar, rode de novo
para atualizar /blog, o sitemap.xml e o llms.txt.
"""
import html
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

SITE = "https://www.clinicaarbia.com.br"
WHATSAPP = "557730171011"
ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "_blog" / "posts"
OUT_DIR = ROOT / "blog"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

ESPECIALISTAS = {
    "Dra. Fabíola Fraga": {
        "cargo": "Dermatologista pela SBD · Cirurgia Dermatológica e Medicina Estética (SBCD)",
        "instagram": "https://www.instagram.com/fabiolafraga.dermato/",
    },
    "Dr. Roberto do Carmo": {
        "cargo": "Dermatologia · Tricologia Médica e Transplante Capilar",
        "instagram": "https://www.instagram.com/drrobertocarmo/",
    },
    "Dra. Vanessa Lins": {
        "cargo": "Angiologia, Cirurgia Vascular e Endovascular",
        "instagram": "https://www.instagram.com/vanessa.llins/",
    },
}


def data_br(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
    return t


def blocks_to_html(lines):
    out, para, lista = [], [], []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if lista:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in lista) + "</ul>")
            lista.clear()

    for ln in lines:
        s = ln.strip()
        if not s:
            flush()
        elif s.startswith("### "):
            flush()
            out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("## "):
            flush()
            out.append(f'<h2 id="{slugify(s[3:])}">{inline(s[3:])}</h2>')
        elif s.startswith("- "):
            if para:
                flush()
            lista.append(s[2:])
        else:
            if lista:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


def slugify(t):
    t = t.lower()
    for a, b in zip("áàâãäéêèíîóôõöúüç", "aaaaaeeeiiooooouuc"):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def texto_puro(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    return re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)


def parse(path):
    raw = path.read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    meta = {}
    for ln in fm.strip().splitlines():
        k, v = ln.split(":", 1)
        meta[k.strip()] = v.strip()
    meta["data"] = date.fromisoformat(meta["data"])

    # separa corpo em seções por "## "
    intro, secoes, atual = [], [], None
    for ln in body.strip().splitlines():
        if ln.startswith("## "):
            atual = [ln[3:].strip(), []]
            secoes.append(atual)
        elif atual is None:
            intro.append(ln)
        else:
            atual[1].append(ln)

    resumo, faq, corpo = [], [], []
    for titulo, linhas in secoes:
        if titulo.lower() == "resumo":
            resumo = [l.strip()[2:] for l in linhas if l.strip().startswith("- ")]
        elif titulo.lower() == "perguntas frequentes":
            q = None
            for l in linhas:
                if l.startswith("### "):
                    q = [l[4:].strip(), []]
                    faq.append(q)
                elif q is not None and l.strip():
                    q[1].append(l.strip())
            faq = [(p, " ".join(r)) for p, r in faq]
        else:
            corpo.append(f"## {titulo}")
            corpo.extend(linhas)

    meta.update(intro=intro, resumo=resumo, faq=faq, corpo=corpo)
    palavras = len(" ".join(intro + corpo + [a for _, a in faq]).split())
    meta["leitura"] = max(2, round(palavras / 200))
    return meta


def wa_link(msg):
    return f"https://wa.me/{WHATSAPP}?text={quote(msg)}"


HEAD = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#01241D">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Clínica ARBIA">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600&family=Cormorant+Garamond:ital,wght@1,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog/blog.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<header class="top">
  <a class="brand" href="/" aria-label="Clínica ARBIA — página inicial"><img src="/logo-arbia-verde.png" alt="Clínica ARBIA" width="105" height="36"></a>
  <nav aria-label="Principal">
    <a href="/">Início</a>
    <a href="/blog"{blog_cur}>Blog</a>
    <a class="btn" href="{wa}" target="_blank" rel="noopener">Agendar consulta ↗</a>
  </nav>
</header>
"""

FOOT = """<footer class="foot">
  <div>
    <a class="brand" href="/"><img src="/logo-arbia-creme.png" alt="Clínica ARBIA" width="140" height="48"></a>
    <p>Dermatologia, Tricologia, Angiologia e Transplante Capilar em Vitória da Conquista, BA.</p>
  </div>
  <address>
    Empresarial Juvenal Leão, 2º andar<br>
    Rua Leôncio Santos, 275, Recreio<br>
    Vitória da Conquista, BA<br>
    <a href="tel:+557730171011">(77) 3017-1011</a> · <a href="https://www.instagram.com/clinicaarbia/">@clinicaarbia</a>
  </address>
  <p class="legal">© {ano} Clínica ARBIA. Conteúdo informativo, não substitui a consulta médica. Responsável técnica: Dra. Fabíola Cristina da Silva Fraga · CRM 20.375.</p>
</footer>
</body>
</html>
"""


def org_ld():
    return {
        "@type": "MedicalClinic",
        "@id": f"{SITE}/#clinica",
        "name": "Clínica ARBIA",
        "url": f"{SITE}/",
        "telephone": "+55-77-3017-1011",
    }


def render_post(p, todos):
    url = f"{SITE}/blog/{p['slug']}"
    esp = ESPECIALISTAS.get(p["especialista"], {})
    msg = f"Olá! Li o artigo \"{p['titulo']}\" no blog e gostaria de agendar uma avaliação na Clínica Arbia."
    wa = wa_link(msg)

    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BlogPosting",
                "headline": p["titulo"],
                "description": p["descricao"],
                "datePublished": p["data"].isoformat(),
                "dateModified": p["data"].isoformat(),
                "inLanguage": "pt-BR",
                "mainEntityOfPage": url,
                "image": f"{SITE}/og.jpg",
                "author": {"@type": "Organization", "name": "Clínica ARBIA", "url": f"{SITE}/"},
                "publisher": org_ld(),
                "about": p["area"],
                "articleSection": p["area"],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Início", "item": f"{SITE}/"},
                    {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE}/blog"},
                    {"@type": "ListItem", "position": 3, "name": p["titulo"], "item": url},
                ],
            },
        ],
    }
    if p["faq"]:
        ld["@graph"].append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": texto_puro(a)}}
                for q, a in p["faq"]
            ],
        })

    h = HEAD.format(
        title=html.escape(f"{p['titulo']} | Clínica ARBIA"), desc=html.escape(p["descricao"]),
        url=url, og_type="article", site=SITE, ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
        blog_cur=' aria-current="page"', wa=html.escape(wa),
    )
    h += '<main class="post">\n'
    h += f'<nav class="crumbs" aria-label="Trilha"><a href="/">Início</a> / <a href="/blog">Blog</a> / <span>{html.escape(p["area"])}</span></nav>\n'
    h += f'<span class="tag">{html.escape(p["area"])}</span>\n'
    h += f'<h1>{html.escape(p["titulo"])}</h1>\n'
    h += (f'<p class="meta"><time datetime="{p["data"].isoformat()}">{data_br(p["data"])}</time>'
          f' · {p["leitura"]} min de leitura · Especialidade na Arbia: {html.escape(p["especialista"])}</p>\n')
    h += '<article>\n'
    h += f'<div class="lead">{blocks_to_html(p["intro"])}</div>\n'
    if p["resumo"]:
        h += ('<aside class="resumo" aria-label="Resumo"><strong>Em resumo</strong><ul>'
              + "".join(f"<li>{inline(i)}</li>" for i in p["resumo"]) + "</ul></aside>\n")
    h += blocks_to_html(p["corpo"]) + "\n"
    if p["faq"]:
        h += '<section class="faq"><h2 id="perguntas-frequentes">Perguntas frequentes</h2>\n'
        for q, a in p["faq"]:
            h += f"<details><summary>{html.escape(q)}</summary><p>{inline(a)}</p></details>\n"
        h += "</section>\n"
    h += "</article>\n"
    h += f"""<section class="cta">
  <span class="tag tag-dark">Agende sua avaliação</span>
  <h2>Converse com quem <em>cuida disso</em> todos os dias.</h2>
  <p>Na Clínica Arbia, {html.escape(p['area'].lower())} é com {html.escape(p['especialista'])}<span class="cargo">{html.escape(esp.get('cargo', ''))}</span></p>
  <a class="btn btn-light" href="{html.escape(wa)}" target="_blank" rel="noopener">Agendar no WhatsApp ↗</a>
</section>
<p class="aviso">Este conteúdo é informativo e não substitui a avaliação médica. Diagnóstico e tratamento são individualizados.</p>
"""
    rel = [o for o in todos if o["slug"] != p["slug"] and o["area"] == p["area"]]
    rel += [o for o in todos if o["slug"] != p["slug"] and o not in rel]
    h += '<section class="rel"><h2>Continue lendo</h2><div class="grid">\n'
    for o in rel[:3]:
        h += card(o)
    h += "</div></section>\n</main>\n"
    h += FOOT.format(ano=p["data"].year)
    return h


def card(o):
    return (f'<a class="card" href="/blog/{o["slug"]}"><span class="tag">{html.escape(o["area"])}</span>'
            f'<h3>{html.escape(o["titulo"])}</h3><p>{html.escape(o["descricao"])}</p>'
            f'<span class="more">Ler artigo · {o["leitura"]} min</span></a>\n')


def render_index(posts):
    url = f"{SITE}/blog"
    desc = ("Artigos da Clínica Arbia sobre pele, cabelo e circulação: dermatologia, tricologia, "
            "transplante capilar e angiologia em Vitória da Conquista.")
    ld = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "Blog da Clínica ARBIA",
        "url": url,
        "inLanguage": "pt-BR",
        "publisher": org_ld(),
        "blogPost": [{"@type": "BlogPosting", "headline": p["titulo"], "url": f"{SITE}/blog/{p['slug']}",
                      "datePublished": p["data"].isoformat()} for p in posts],
    }
    wa = wa_link("Olá! Gostaria de agendar uma consulta na Clínica Arbia.")
    h = HEAD.format(title="Blog | Clínica ARBIA — Dermatologia, Tricologia e Angiologia", desc=html.escape(desc),
                    url=url, og_type="website", site=SITE, ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
                    blog_cur=' aria-current="page"', wa=html.escape(wa))
    areas = sorted({p["area"] for p in posts})
    h += '<main class="blog">\n<section class="hero">\n<span class="tag">Blog da Arbia</span>\n'
    h += '<h1>Cuidado além da <em>superfície.</em></h1>\n'
    h += ('<p>Informação clara sobre pele, cabelo e circulação, escrita a partir do que '
          'atendemos todos os dias. Para entender, tirar dúvidas e saber quando é hora de uma avaliação.</p>\n</section>\n')
    h += '<div class="filtros" role="list">' + "".join(
        f'<a role="listitem" href="#{slugify(a)}">{html.escape(a)}</a>' for a in areas) + "</div>\n"
    for a in areas:
        h += f'<section class="area" id="{slugify(a)}"><h2>{html.escape(a)}</h2><div class="grid">\n'
        for p in posts:
            if p["area"] == a:
                h += card(p)
        h += "</div></section>\n"
    h += "</main>\n" + FOOT.format(ano=date.today().year)
    return h


def write_sitemap(posts):
    urls = [(f"{SITE}/", None), (f"{SITE}/blog", None), (f"{SITE}/instagram", None), (f"{SITE}/galeria", None)]
    urls += [(f"{SITE}/blog/{p['slug']}", p["data"].isoformat()) for p in posts]
    x = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d in urls:
        x.append(f"  <url><loc>{u}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>")
    x.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(x) + "\n", encoding="utf-8")


def write_llms(posts):
    base = (ROOT / "_blog" / "llms-base.md").read_text(encoding="utf-8").rstrip()
    linhas = [base, "", "## Blog", ""]
    for p in posts:
        linhas.append(f"- [{p['titulo']}]({SITE}/blog/{p['slug']}): {p['descricao']}")
    (ROOT / "llms.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main():
    posts = sorted((parse(f) for f in POSTS_DIR.glob("*.md")), key=lambda p: (p["data"], p["titulo"]), reverse=True)
    OUT_DIR.mkdir(exist_ok=True)
    for p in posts:
        (OUT_DIR / f"{p['slug']}.html").write_text(render_post(p, posts), encoding="utf-8")
    (OUT_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    write_sitemap(posts)
    write_llms(posts)
    print(f"{len(posts)} posts gerados em {OUT_DIR}")


if __name__ == "__main__":
    main()
