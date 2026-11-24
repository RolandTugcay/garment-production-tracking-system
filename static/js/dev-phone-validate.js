// /**
//  * Attaches live auto-formatting (####-###-####) and validation to a phone input.
//  *
//  * @param {HTMLInputElement|string} input - The input element or CSS selector.
//  * @param {Object} [options] - Optional configuration.
//  * @param {HTMLElement|string} [options.feedbackEl] - Element or selector to display status text.
//  * @param {RegExp} [options.pattern] - Custom regex pattern (defaults to ####-###-####).
//  * @param {string} [options.validMessage] - Message shown when valid.
//  * @param {string} [options.invalidMessage] - Message shown when invalid.
//  * @returns {Function} A validation check function you can call manually (e.g., on form submit).
//  */

function attachPhoneValidator(input, options = {}) {
    const inputEl = typeof input === 'string' ? document.querySelector(input) : input;
    if (!inputEl) return () => false;

    const feedbackEl = typeof options.feedbackEl === 'string'
    ? document.querySelector(options.feedbackEl)
    : options.feedbackEl;

    const pattern = options.pattern || /^\d{4}-\d{3}-\d{4}$/;
    const validMessage = options.validMessage ?? '';
    const invalidMessage = options.invalidMessage ?? '';

    const formatDigits = (value) => {
    const digits = value.replace(/\D/g, '').slice(0, 11);
    if (digits.length > 7) {
        return `${digits.slice(0, 4)}-${digits.slice(4, 7)}-${digits.slice(7)}`;
    }
    if (digits.length > 4) {
        return `${digits.slice(0, 4)}-${digits.slice(4)}`;
    }
    return digits;
    };

    const validate = () => {
    const val = inputEl.value;
    const isValid = pattern.test(val);

    if (val.length === 0) {
        inputEl.classList.remove('is-valid', 'is-invalid');
        if (feedbackEl) {
        feedbackEl.textContent = '';
        feedbackEl.className = 'feedback';
        }
        return false;
    }

    inputEl.classList.toggle('is-valid', isValid);
    inputEl.classList.toggle('is-invalid', !isValid);

    if (feedbackEl) {
        feedbackEl.textContent = isValid ? validMessage : invalidMessage;
        feedbackEl.className = `feedback ${isValid ? 'valid' : 'invalid'}`;
    }

    return isValid;
    };

    inputEl.addEventListener('input', () => {
    inputEl.value = formatDigits(inputEl.value);
    validate();
    });

    if (inputEl.value) {
    inputEl.value = formatDigits(inputEl.value);
    validate();
    }

    return validate;
}