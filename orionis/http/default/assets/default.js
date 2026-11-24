/* Progressive enhancements only: all request and exception data is rendered by Jinja. */
(function () {
    'use strict';

    function startClock() {
        var clock = document.getElementById('systemTime');
        var timezone = clock?.dataset.timezone;
        if (!timezone) {
            return;
        }
        var formatter;
        try {
            formatter = new Intl.DateTimeFormat(undefined, {
                timeZone: timezone,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hourCycle: 'h23',
                timeZoneName: 'short'
            });
        } catch (error) {
            // An older browser may lack this IANA zone. Keep the server-rendered label.
            return;
        }
        function tick() {
            var now = new Date();
            clock.textContent = formatter.format(now);
            clock.setAttribute('datetime', now.toISOString());
        }
        tick();
        window.setInterval(tick, 1000);
    }

    function enableTraceNavigation() {
        var frames = document.querySelectorAll('[data-trace-frame]');
        var links = document.querySelectorAll('[data-frame-target]');
        if (!frames.length || !links.length) {
            return;
        }
        function selectFrame(id) {
            var selected = document.getElementById(id);
            if (selected?.dataset.traceFrame === undefined) {
                return false;
            }
            for (const frame of frames) {
                if (frame === selected) {
                    frame.removeAttribute('hidden');
                } else {
                    frame.setAttribute('hidden', '');
                }
            }
            for (const link of links) {
                if (link.dataset.frameTarget === id) {
                    link.setAttribute('aria-current', 'true');
                } else {
                    link.removeAttribute('aria-current');
                }
            }
            return true;
        }
        function followFrame(event) {
            // Preserve opening a frame link in another tab and native anchor navigation.
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
                return;
            }
            if (selectFrame(this.dataset.frameTarget)) {
                event.preventDefault();
                var selected = document.getElementById(this.dataset.frameTarget);
                selected.focus({ preventScroll: true });
                selected.scrollIntoView({ block: 'nearest' });
            }
        }
        function selectLocationFrame() {
            var id = window.location.hash.slice(1);
            if (!selectFrame(id)) {
                selectFrame(frames[0].id);
            }
        }
        for (const link of links) {
            link.addEventListener('click', followFrame);
        }
        selectLocationFrame();
        window.addEventListener('hashchange', selectLocationFrame);
    }

    function copyText(button, status, text, messages) {
        button.disabled = true;
        status.textContent = '';
        delete status.dataset.copyState;
        navigator.clipboard.writeText(text).then(function () {
            button.disabled = false;
            button.title = messages.copiedTitle;
            status.dataset.copyState = 'success';
            status.textContent = messages.success;
        }, function () {
            button.disabled = false;
            button.title = messages.copyTitle;
            status.dataset.copyState = 'error';
            status.textContent = messages.error;
        });
    }

    function enableCopyReport() {
        var button = document.getElementById('copy-exception');
        var status = document.getElementById('copy-status');
        if (!button || !status || !navigator.clipboard?.writeText) {
            return;
        }
        button.removeAttribute('hidden');
        button.addEventListener('click', function () {
            var report = [
                document.getElementById('main-error').textContent,
                document.getElementById('main-description').textContent,
                document.getElementById('request-method').textContent + ' ' +
                document.getElementById('request-path').textContent
            ];
            var frames = document.querySelectorAll('[data-trace-frame]');
            for (const frame of frames) {
                var values = frame.querySelectorAll('.file-info-value');
                report.push('\n' + values[0].textContent.trim() + ':' + values[1].textContent.trim());
                for (const row of frame.querySelectorAll('.source-row')) {
                    report.push(row.querySelector('.source-number').textContent + ' ' +
                        row.querySelector('.source-code').textContent);
                }
            }
            copyText(button, status, report.join('\n'), {
                copyTitle: 'Copy exception report',
                copiedTitle: 'Report copied',
                success: 'Exception report copied.',
                error: 'The exception report could not be copied.'
            });
        });
    }

    function copyDump() {
        var panel = this.closest('.dump-panel');
        var code = panel.querySelector('.dump-output code');
        var status = panel.querySelector('[data-dump-copy-status]');
        copyText(this, status, code.textContent, {
            copyTitle: 'Copy dump content',
            copiedTitle: 'Dump content copied',
            success: 'Copied',
            error: 'Copy failed'
        });
    }

    function enableDumpCopy() {
        var template = document.getElementById('dump-copy-action');
        if (!template || !navigator.clipboard?.writeText) {
            return;
        }
        for (const panel of document.querySelectorAll('.dump-panel')) {
            var action = template.content.cloneNode(true);
            action.querySelector('[data-copy-dump]').addEventListener('click', copyDump);
            panel.querySelector('.code-header-info').appendChild(action);
        }
    }

    const sourceKeywords = new Set([
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
        'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
        'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
    ]);

    function sourceToken(match, source) {
        const text = match[0];
        if (text === '"' || text === "'") {
            // Match a complete string at this quote. Leave an unmatched quote as plain text.
            const quoted = text === '"' ? /"(?:[^"\\\r\n]|\\[^\r\n])*"/y : /'(?:[^'\\\r\n]|\\[^\r\n])*'/y;
            quoted.lastIndex = match.index;
            const literal = quoted.exec(source);
            return literal && { text: literal[0], className: 'syntax-string' };
        }
        if (text.startsWith('#')) {
            return { text, className: 'syntax-comment' };
        }
        if (/^\d/.test(text)) {
            return { text, className: 'syntax-number' };
        }
        return sourceKeywords.has(text) ? { text, className: 'syntax-keyword' } : null;
    }

    function highlightBlock(block) {
        const source = block.textContent;
        if (source.length > 20000) {
            return;
        }
        const candidates = /#[^\r\n]*|["']|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*/g;
        const fragment = document.createDocumentFragment();
        let cursor = 0;
        let match;
        while ((match = candidates.exec(source)) !== null) {
            const token = sourceToken(match, source);
            if (!token) {
                continue;
            }
            fragment.appendChild(document.createTextNode(source.slice(cursor, match.index)));
            const span = document.createElement('span');
            span.className = token.className;
            span.textContent = token.text;
            fragment.appendChild(span);
            cursor = match.index + token.text.length;
            candidates.lastIndex = cursor;
        }
        fragment.appendChild(document.createTextNode(source.slice(cursor)));
        block.replaceChildren(fragment);
    }

    function highlightSource() {
        for (const block of document.querySelectorAll('code.source-code')) {
            highlightBlock(block);
        }
    }

    function initialize() {
        startClock();
        enableTraceNavigation();
        highlightSource();
        enableCopyReport();
        enableDumpCopy();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
}());
