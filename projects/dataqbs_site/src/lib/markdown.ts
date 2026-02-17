/**
 * Lightweight markdown → HTML renderer for chat messages.
 * Handles: code blocks, inline code, bold, italic, links, lists, line breaks.
 * No external dependencies.
 */
export function renderMarkdown(raw: string): string {
  let html = escapeHtml(raw);

  // Fenced code blocks: ```lang\n...\n```
  html = html.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    (_m, lang, code) =>
      `<pre class="chat-code-block"><code class="language-${lang}">${code.trim()}</code></pre>`,
  );

  // Inline code: `...`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold: **...**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic: *...*
  html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');

  // Links: [text](url)
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
  );

  // Unordered lists: lines starting with - or *
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

  // Ordered lists: lines starting with 1. 2. etc.
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Paragraphs: double newlines
  html = html.replace(/\n{2,}/g, '</p><p>');

  // Single newlines → <br>
  html = html.replace(/\n/g, '<br>');

  return `<p>${html}</p>`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
