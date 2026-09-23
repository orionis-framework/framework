/* Progressive enhancements only: all request and exception data is rendered by Jinja. */
(function () {
    'use strict';

    function startClock() {
        var clock = document.getElementById('systemTime');
        if (!clock) {
            return;
        }
        function tick() {
            var now = new Date();
            clock.textContent = now.toUTCString().slice(17, 25) + ' UTC';
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
            if (!selected || !selected.hasAttribute('data-trace-frame')) {
                return false;
            }
            var index;
            for (index = 0; index < frames.length; index += 1) {
                if (frames[index] === selected) {
                    frames[index].removeAttribute('hidden');
                } else {
                    frames[index].setAttribute('hidden', '');
                }
            }
            for (index = 0; index < links.length; index += 1) {
                if (links[index].getAttribute('data-frame-target') === id) {
                    links[index].setAttribute('aria-current', 'true');
                } else {
                    links[index].removeAttribute('aria-current');
                }
            }
            return true;
        }
        function followFrame(event) {
            // Preserve opening a frame link in another tab and native anchor navigation.
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
                return;
            }
            if (selectFrame(this.getAttribute('data-frame-target'))) {
                event.preventDefault();
            }
        }
        function selectLocationFrame() {
            var id = window.location.hash.slice(1);
            if (!selectFrame(id)) {
                selectFrame(frames[0].id);
            }
        }
        for (var index = 0; index < links.length; index += 1) {
            links[index].addEventListener('click', followFrame);
        }
        selectLocationFrame();
        window.addEventListener('hashchange', selectLocationFrame);
    }

    function highlightSource() {
        // A small cosmetic tokenizer. Source text is only ever inserted as text nodes.
        var tokens = /#[^\r\n]*|"(?:[^"\\\r\n]|\\[^\r\n])*"|'(?:[^'\\\r\n]|\\[^\r\n])*'|\b(?:False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b|\b\d+(?:\.\d+)?\b/g;
        var blocks = document.querySelectorAll('code.source-code');
        for (var index = 0; index < blocks.length; index += 1) {
            var block = blocks[index];
            var source = block.textContent;
            // Keep unusually large source lines readable without expensive highlighting.
            if (source.length > 20000) {
                continue;
            }
            var fragment = document.createDocumentFragment();
            var cursor = 0;
            var match;
            tokens.lastIndex = 0;
            while ((match = tokens.exec(source)) !== null) {
                fragment.appendChild(document.createTextNode(source.slice(cursor, match.index)));
                var token = document.createElement('span');
                var first = match[0].charAt(0);
                token.className = first === '#' ? 'syntax-comment' :
                    (first === '"' || first === "'") ? 'syntax-string' :
                    /[0-9]/.test(first) ? 'syntax-number' : 'syntax-keyword';
                token.textContent = match[0];
                fragment.appendChild(token);
                cursor = tokens.lastIndex;
            }
            fragment.appendChild(document.createTextNode(source.slice(cursor)));
            while (block.firstChild) {
                block.removeChild(block.firstChild);
            }
            block.appendChild(fragment);
        }
    }

    function initialize() {
        startClock();
        enableTraceNavigation();
        highlightSource();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
}());
