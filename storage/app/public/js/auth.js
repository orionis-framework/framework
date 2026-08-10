window.addEventListener("load", (event) => {

    /**
     * Prefill the email field with the remembered username on the login page.
     */
    if (window.location.pathname === '/login') {
        const email = document.getElementById('email');
        const cookie = document.cookie
            .split('; ')
            .find((entry) => entry.startsWith('usrname='));

        if (email && cookie && !email.value) {
            email.value = decodeURIComponent(cookie.slice('usrname='.length));
        }
    }

    /**
     * Toggle password visibility when the toggle button is clicked.
     */
    document.addEventListener('click', (event) => {
        const toggle = event.target.closest('[data-password-toggle]');

        if (!toggle) {
            return;
        }

        event.preventDefault();

        const input = document.getElementById(toggle.dataset.passwordToggle);

        if (!input) {
            return;
        }

        const revealing = input.type === 'password';
        input.type = revealing ? 'text' : 'password';

        toggle.querySelector('[data-password-icon="show"]').classList.toggle('d-none', revealing);
        toggle.querySelector('[data-password-icon="hide"]').classList.toggle('d-none', !revealing);

        const label = revealing ? toggle.dataset.labelHide : toggle.dataset.labelShow;
        toggle.setAttribute('title', label);
        toggle.setAttribute('aria-label', label);
    });

});

