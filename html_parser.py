import random
import time
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from readability import Document
from typing import Dict, Any, List, Optional, Sequence, Tuple, Union, Set
from urllib.parse import urljoin, urlparse
from utils import setup_logging, clean_text, format_size

logger = setup_logging()


class HTMLParser:
    """Classe per analizzare e recuperare contenuti HTML"""

    NOISE_KEYWORDS: Sequence[str] = (
        'nav', 'menu', 'footer', 'header', 'subscribe', 'metered', 'paywall',
        'share', 'social', 'toolbar', 'breadcrumbs', 'breadcrumb', 'cookie',
        'banner', 'popup', 'modal', 'adv', 'advert', 'ads', 'sponsor',
        'related', 'recommend', 'newsletter', 'comment', 'comments', 'form-',
        'promo', 'utility', 'widget', 'sidebar', 'login', 'signup', 'consent',
        'gdpr', 'tracking', 'notification', 'overlay', 'player-controls',
        'gallery', 'carousel', 'slider', 'tags', 'taglist', 'pagination'
    )
    ARTICLE_HINTS: Sequence[str] = (
        'article', 'story', 'content', 'body', 'post', 'entry', 'main',
        'text', 'read', 'news', 'detail'
    )
    REALISTIC_USER_AGENTS: Sequence[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )

    def __init__(self, timeout=10, user_agent=None):
        """
        Inizializza il parser HTML

        Args:
            timeout: Timeout in secondi per le richieste
            user_agent: User-Agent personalizzato per le richieste HTTP
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.user_agents: List[str] = self._normalize_user_agents(user_agent)
        self.session.headers.update({'User-Agent': self.user_agents[0]})

    def fetch_page(self, url: str) -> Tuple[Dict[str, Any], str]:
        """
        Recupera il contenuto di una pagina web

        Args:
            url: URL della pagina da recuperare

        Returns:
            Dizionario con informazioni sulla pagina e il suo contenuto
        """
        logger.info(f"Recupero pagina: {url}")

        try:
            self._wait_between_requests()
            user_agent = self._choose_user_agent()
            self.session.headers.update({'User-Agent': user_agent})
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()

            page_info = {
                'url': response.url,
                'status_code': response.status_code,
                'encoding': response.encoding,
                'size_bytes': len(response.content),
                'size_readable': format_size(len(response.content)),
                'headers': dict(response.headers)
            }

            return page_info, response.text

        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante il recupero della pagina: {e}")
            raise e

    def parse_html(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Analizza il contenuto HTML e si concentra sull'articolo principale.
        """
        logger.info("Analisi HTML in corso...")

        try:
            soup = BeautifulSoup(html_content, 'lxml')
            content_soup = self._prepare_content_soup(html_content)

            parsed_info = {
                'title': clean_text(soup.title.string) if soup.title else "",
                'base_url': url,
                'domain': urlparse(url).netloc,
                'meta': self._extract_meta(soup)
            }

            readability_content = self._extract_main_content(html_content)
            content_blocks = self._extract_content_blocks(content_soup)
            schema_block = self._extract_schema_block(content_soup)
            if schema_block:
                content_blocks.insert(0, schema_block)

            article_section = self._build_article_section(
                readability_content,
                content_blocks,
                parsed_info['title'],
                parsed_info['meta'],
                content_soup,
                url
            )

            parsed_info.update({
                'article': article_section,
                'context': self._build_page_context(content_soup, url, article_section, content_blocks)
            })

            return parsed_info

        except Exception as e:
            logger.error(f"Errore durante l'analisi HTML: {e}")
            raise e

    def _extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Estrae i meta tag dalla pagina"""
        meta_tags = {}

        for tag in soup.find_all('meta'):
            if tag.get('name') and tag.get('content'):
                meta_tags[tag['name']] = tag['content']
            elif tag.get('property') and tag.get('content'):
                meta_tags[tag['property']] = tag['content']
            elif tag.get('charset'):
                meta_tags['charset'] = tag['charset']

        return meta_tags

    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        headings = {'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []}
        for level in range(1, 7):
            for heading in soup.find_all(f'h{level}'):
                headings[f'h{level}'].append(clean_text(heading.get_text()))
        return headings

    def _extract_links(self, soup: BeautifulSoup, base_url: str, limit: int = 100) -> List[Dict[str, str]]:
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            links.append({
                'text': clean_text(link.get_text()),
                'href': absolute_url,
                'is_external': urlparse(base_url).netloc != urlparse(absolute_url).netloc,
                'title': link.get('title', '')
            })
            if len(links) >= limit:
                break
        return links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if src:
                absolute_url = urljoin(base_url, src)
                images.append({
                    'src': absolute_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width', ''),
                    'height': img.get('height', '')
                })
        return images

    def _extract_tables(self, html_fragment: Union[str, BeautifulSoup]) -> List[Dict[str, Any]]:
        tables: List[Dict[str, Any]] = []
        if not html_fragment:
            return tables
        soup = html_fragment if isinstance(html_fragment, BeautifulSoup) else BeautifulSoup(html_fragment, 'lxml')
        for i, table in enumerate(soup.find_all('table')):
            table_data = {
                'id': i,
                'headers': [],
                'rows': []
            }
            headers = table.find_all('th')
            if headers:
                table_data['headers'] = [clean_text(h.get_text()) for h in headers]
            for row in table.find_all('tr'):
                row_data = [clean_text(cell.get_text()) for cell in row.find_all(['td', 'th'])]
                if row_data:
                    table_data['rows'].append(row_data)
            tables.append(table_data)
        return tables

    def _extract_lists(self, html_fragment: Union[str, BeautifulSoup]) -> Dict[str, List[List[str]]]:
        lists: Dict[str, List[List[str]]] = {'ul': [], 'ol': []}
        if not html_fragment:
            return lists
        soup = html_fragment if isinstance(html_fragment, BeautifulSoup) else BeautifulSoup(html_fragment, 'lxml')
        for ul in soup.find_all('ul'):
            items = [clean_text(li.get_text()) for li in ul.find_all('li') if clean_text(li.get_text())]
            if items:
                lists['ul'].append(items)
        for ol in soup.find_all('ol'):
            items = [clean_text(li.get_text()) for li in ol.find_all('li') if clean_text(li.get_text())]
            if items:
                lists['ol'].append(items)
        return lists

    def _prepare_content_soup(self, html_content: str) -> BeautifulSoup:
        """Crea una versione ripulita del DOM rimuovendo elementi rumorosi."""
        soup = BeautifulSoup(html_content, 'lxml')
        for element in soup(['script', 'style', 'noscript', 'iframe', 'svg', 'canvas']):
            element.decompose()
        for element in soup.find_all(True):
            if self._should_skip_element(element):
                element.decompose()
        return soup

    def _should_skip_element(self, element: Tag) -> bool:
        if not isinstance(element, Tag):
            return False
        if element.name in {'nav', 'header', 'footer', 'aside'}:
            return True
        attr_map = element.attrs or {}
        role = (attr_map.get('role') or '').lower()
        if role in {'navigation', 'banner', 'complementary', 'contentinfo', 'search'}:
            return True
        attributes: List[str] = []
        for attr in ('class', 'id', 'name', 'aria-label', 'data-track-label', 'data-component', 'data-testid'):
            value = attr_map.get(attr)
            if isinstance(value, list):
                attributes.extend([str(v).lower() for v in value if v])
            elif value:
                attributes.append(str(value).lower())
        if attributes:
            attrs = " ".join(attributes)
            if any(keyword in attrs for keyword in self.NOISE_KEYWORDS):
                if any(hint in attrs for hint in self.ARTICLE_HINTS):
                    return False
                return True
        return False

    def _extract_main_content(self, html_content: str) -> Dict[str, Any]:
        try:
            document = Document(html_content)
            summary_html = document.summary()
            summary_soup = BeautifulSoup(summary_html, 'lxml')
            paragraphs = [
                clean_text(p.get_text())
                for p in summary_soup.find_all(['p', 'li'])
                if clean_text(p.get_text())
            ]
            text = "\n\n".join(paragraphs).strip()
            if not text:
                return {}
            word_count = len(text.split())
            return {
                'source': 'readability',
                'title': clean_text(document.title()) or "",
                'short_title': clean_text(document.short_title()) or "",
                'summary_html': summary_html,
                'text': text,
                'paragraphs': paragraphs,
                'word_count': word_count,
                'reading_time_minutes': self._estimate_reading_time(word_count),
                'confidence': min(0.95, 0.6 + word_count / 1500)
            }
        except Exception as exc:
            logger.debug(f"Readability non disponibile: {exc}")
            return {}

    def _extract_content_blocks(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for idx, element in enumerate(soup.find_all(['article', 'main', 'section', 'div'])):
            if self._should_skip_element(element):
                continue
            block = self._build_block_info(element, idx)
            if block:
                candidates.append(block)
        candidates.sort(key=lambda item: item['score'], reverse=True)
        return candidates[:10]

    def _build_block_info(self, element: Tag, idx: Union[int, str]) -> Optional[Dict[str, Any]]:
        if not element or not isinstance(element, Tag):
            return None
        text = clean_text(element.get_text(" ", strip=True))
        word_count = len(text.split())
        if word_count < 40:
            return None
        link_text = " ".join(clean_text(a.get_text(" ", strip=True)) for a in element.find_all('a'))
        link_density = len(link_text) / max(len(text), 1)
        paragraphs = [
            clean_text(p.get_text())
            for p in element.find_all('p')
            if clean_text(p.get_text())
        ]
        heading = element.find(['h1', 'h2', 'h3'])
        heading_text = clean_text(heading.get_text()) if heading else ""
        score = self._score_block(word_count, link_density, len(paragraphs), heading_text)
        block_html = element.decode()
        return {
            'id': f'block_{idx}',
            'tag': element.name,
            'classes': element.get('class', []),
            'dom_path': self._compute_dom_path(element),
            'heading': heading_text,
            'paragraphs': paragraphs,
            'html': block_html,
            'text_preview': text[:280] + ('...' if len(text) > 280 else ''),
            'word_count': word_count,
            'link_density': round(link_density, 3),
            'score': round(score, 2)
        }

    def _score_block(self, word_count: int, link_density: float, paragraph_count: int, heading: str) -> float:
        heading_bonus = 1.25 if heading else 1.0
        paragraph_bonus = 1 + min(paragraph_count, 5) * 0.1
        link_penalty = 1.0 - min(link_density, 0.9)
        return word_count * heading_bonus * paragraph_bonus * link_penalty

    def _compute_dom_path(self, element: Tag) -> str:
        parts: List[str] = []
        current: Optional[Tag] = element
        depth = 0
        while current and isinstance(current, Tag) and depth < 5:
            parent = current.parent if isinstance(current.parent, Tag) else None
            index = 0
            if parent:
                siblings = [sib for sib in parent.find_all(current.name, recursive=False)]
                for idx, sib in enumerate(siblings):
                    if sib is current:
                        index = idx
                        break
            identifier = current.get('id') or ""
            class_attr = current.get('class') or []
            cls = ".".join(class_attr[:2]) if isinstance(class_attr, list) else ""
            descriptor = current.name
            if identifier:
                descriptor += f"#{identifier}"
            elif cls:
                descriptor += f".{cls}"
            descriptor += f"[{index}]"
            parts.append(descriptor)
            current = parent
            depth += 1
        return " > ".join(parts)

    def _choose_main_content(
        self,
        readability_content: Dict[str, Any],
        blocks: List[Dict[str, Any]],
        fallback_title: str
    ) -> Dict[str, Any]:
        readability_words = readability_content.get('word_count', 0) if readability_content else 0
        if readability_content and readability_words >= 80:
            readability_content.setdefault('title', fallback_title)
            return readability_content
        if blocks:
            best = blocks[0]
            text = "\n\n".join(best['paragraphs']).strip() or best['text_preview']
            word_count = best['word_count'] if best['word_count'] else len(text.split())
            return {
                'source': 'heuristic',
                'title': best.get('heading') or fallback_title,
                'text': text,
                'paragraphs': best['paragraphs'],
                'word_count': word_count,
                'score': best['score'],
                'dom_path': best['dom_path'],
                'html': best.get('html'),
                'reading_time_minutes': self._estimate_reading_time(word_count),
                'confidence': min(0.85, 0.4 + min(best['score'] / 1500, 0.45))
            }
        return readability_content or {
            'source': 'unknown',
            'title': fallback_title,
            'text': '',
            'paragraphs': [],
            'word_count': 0,
            'reading_time_minutes': 0,
            'confidence': 0.2
        }

    def _build_article_section(
        self,
        readability_content: Dict[str, Any],
        blocks: List[Dict[str, Any]],
        fallback_title: str,
        meta: Dict[str, Any],
        content_soup: BeautifulSoup,
        base_url: str
    ) -> Dict[str, Any]:
        main_content = self._choose_main_content(readability_content, blocks, fallback_title)
        metadata = self._extract_article_metadata(content_soup, meta)
        media = self._extract_article_media(main_content, meta, base_url, content_soup)
        excerpt_value: Optional[str] = metadata.get('excerpt')
        if not excerpt_value:
            paragraphs = main_content.get('paragraphs') or []
            excerpt_value = paragraphs[0] if paragraphs else ''
        article_links = self._extract_links_from_main(main_content, base_url)
        lists = self._extract_lists(main_content.get('summary_html') or main_content.get('html', ''))
        tables = self._extract_tables(main_content.get('summary_html') or main_content.get('html', ''))

        body = {
            'text': main_content.get('text', '').strip(),
            'paragraphs': main_content.get('paragraphs', []),
            'word_count': main_content.get('word_count', 0),
            'reading_time_minutes': main_content.get('reading_time_minutes', self._estimate_reading_time(main_content.get('word_count', 0))),
            'source': main_content.get('source'),
            'html': main_content.get('summary_html') or main_content.get('html', '')
        }

        stats = {
            'confidence': round(main_content.get('confidence', 0.4), 2),
            'paragraph_count': len(body['paragraphs']),
            'has_media': bool(media.get('hero_image') or media.get('videos')),
            'has_links': bool(article_links)
        }

        article = {
            'title': main_content.get('title') or metadata.get('title') or fallback_title,
            'subtitle': metadata.get('subtitle'),
            'section': metadata.get('section'),
            'authors': metadata.get('authors', []),
            'published_at': metadata.get('published_at'),
            'updated_at': metadata.get('updated_at'),
            'excerpt': clean_text(excerpt_value) if excerpt_value else "",
            'keywords': metadata.get('keywords', []),
            'tags': metadata.get('tags', []),
            'body': body,
            'media': media,
            'links': article_links,
            'lists': lists,
            'tables': tables,
            'stats': stats
        }
        return article

    def _extract_links_from_main(self, main_content: Dict[str, Any], base_url: str) -> List[Dict[str, str]]:
        html_fragment = main_content.get('summary_html') or main_content.get('html')
        if not html_fragment:
            return []
        soup = BeautifulSoup(html_fragment, 'lxml')
        return self._extract_links(soup, base_url, limit=40)

    def _extract_article_metadata(self, soup: BeautifulSoup, meta: Dict[str, Any]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        metadata['title'] = meta.get('og:title') or meta.get('twitter:title') or meta.get('title')
        metadata['subtitle'] = self._find_subtitle(soup)
        metadata['authors'] = self._find_authors(soup, meta)
        published, updated = self._find_dates(soup, meta)
        metadata['published_at'] = published
        metadata['updated_at'] = updated
        metadata['section'] = meta.get('article:section') or meta.get('category-label')
        metadata['excerpt'] = meta.get('description') or meta.get('og:description')
        metadata['keywords'] = self._split_meta_values(meta.get('news_keywords') or meta.get('keywords'))
        metadata['tags'] = self._split_meta_values(meta.get('article:tag') or meta.get('parsely-tags'))
        return metadata

    def _find_subtitle(self, soup: BeautifulSoup) -> Optional[str]:
        subtitle = soup.find(['h2', 'p'], class_=lambda value: value and 'subtitle' in value.lower())
        if subtitle:
            return clean_text(subtitle.get_text())
        possible = soup.select_one('[data-testid*="subtitle"], .article-subtitle, .story__summary, .lead')
        return clean_text(possible.get_text()) if possible else None

    def _find_authors(self, soup: BeautifulSoup, meta: Dict[str, Any]) -> List[str]:
        authors: List[str] = []
        meta_candidates = [
            meta.get('author'),
            meta.get('article:author'),
            meta.get('parsely-author')
        ]
        for candidate in meta_candidates:
            if candidate:
                authors.extend([name.strip() for name in candidate.split(',') if name.strip()])
        if authors:
            return list(dict.fromkeys(authors))
        dom_candidates = soup.select('[itemprop="author"], .author-name, .byline, [rel="author"]')
        for element in dom_candidates:
            text = clean_text(element.get_text())
            if text and text.lower() not in ('di', 'by'):
                authors.append(text)
        return list(dict.fromkeys(authors))

    def _find_dates(self, soup: BeautifulSoup, meta: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        published = meta.get('article:published_time') or meta.get('pubdate') or meta.get('parsely-pub-date')
        updated = meta.get('article:modified_time') or meta.get('last-modified')
        if not published:
            time_tag = soup.find('time', attrs={'datetime': True})
            if time_tag:
                published = time_tag.get('datetime') or clean_text(time_tag.get_text())
        if not updated:
            updated_tag = soup.find('time', attrs={'itemprop': 'dateModified'})
            if updated_tag:
                updated = updated_tag.get('datetime') or clean_text(updated_tag.get_text())
        return published, updated

    def _split_meta_values(self, value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]

    def _extract_article_media(
        self,
        main_content: Dict[str, Any],
        meta: Dict[str, Any],
        base_url: str,
        soup: BeautifulSoup
    ) -> Dict[str, Any]:
        media: Dict[str, Any] = {'hero_image': None, 'gallery': [], 'videos': []}
        hero = meta.get('og:image') or meta.get('twitter:image') or meta.get('image_thumb_src')
        if hero:
            media['hero_image'] = urljoin(base_url, hero)
        fragment = main_content.get('summary_html') or main_content.get('html')
        if fragment:
            fragment_soup = BeautifulSoup(fragment, 'lxml')
            for img in fragment_soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    absolute = urljoin(base_url, src)
                    media['gallery'].append({
                        'src': absolute,
                        'alt': clean_text(img.get('alt', '')),
                        'title': clean_text(img.get('title', ''))
                    })
            for video in fragment_soup.find_all('video'):
                source = video.find('source')
                src = source.get('src') if source else video.get('src')
                if src:
                    media['videos'].append(urljoin(base_url, src))
        iframe = soup.find('iframe', attrs={'src': True})
        if iframe:
            media['videos'].append(urljoin(base_url, iframe.get('src')))
        media['gallery'] = media['gallery'][:5]
        media['videos'] = media['videos'][:3]
        return media

    def _estimate_reading_time(self, word_count: int) -> float:
        if word_count <= 0:
            return 0
        return round(max(word_count / 200, 0.1), 2)

    def _extract_schema_block(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        selectors = [
            '[itemprop="articleBody"]',
            '[itemtype*="Article"]',
            'article',
            '[role="main"]',
            '.article-body',
            '.story__content',
            '.article__content'
        ]
        for idx, selector in enumerate(selectors):
            element = soup.select_one(selector)
            if element and not self._should_skip_element(element):
                block = self._build_block_info(element, f'schema_{idx}')
                if block:
                    return block
        return None

    def _build_page_context(
        self,
        soup: BeautifulSoup,
        base_url: str,
        article_section: Dict[str, Any],
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        primary_links = article_section.get('links', [])
        context = {
            'headings': self._extract_headings(soup),
            'related_links': self._build_related_links(soup, base_url, primary_links),
            'candidates': self._summarize_blocks(blocks)
        }
        return context

    def _build_related_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
        primary_links: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        seen: Set[str] = {link['href'] for link in primary_links}
        related: List[Dict[str, str]] = []
        for link in self._extract_links(soup, base_url, limit=60):
            if link['href'] in seen or not link['text']:
                continue
            related.append(link)
            if len(related) >= 15:
                break
        return related

    def _summarize_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        summary: List[Dict[str, Any]] = []
        for block in blocks[:5]:
            summary.append({
                'id': block.get('id'),
                'heading': block.get('heading'),
                'word_count': block.get('word_count'),
                'score': block.get('score'),
                'dom_path': block.get('dom_path')
            })
        return summary

    def _normalize_user_agents(self, user_agent: Optional[Union[str, Sequence[str]]]) -> List[str]:
        """Normalizza l'input user-agent creando una lista da ruotare."""
        if isinstance(user_agent, str):
            ua_list = [user_agent.strip()] if user_agent.strip() else []
        elif isinstance(user_agent, Sequence):
            ua_list = [ua.strip() for ua in user_agent if isinstance(ua, str) and ua.strip()]
        else:
            ua_list = []
        if not ua_list:
            ua_list = list(self.REALISTIC_USER_AGENTS)
        return ua_list

    def _choose_user_agent(self) -> str:
        """Restituisce un user-agent casuale per distribuire le richieste."""
        if not self.user_agents:
            self.user_agents = list(self.REALISTIC_USER_AGENTS)
        return random.choice(self.user_agents)

    def _wait_between_requests(self) -> None:
        """Inserisce un piccolo jitter tra le richieste per sembrare più umano."""
        delay = random.uniform(0.15, 0.45)
        time.sleep(delay)
