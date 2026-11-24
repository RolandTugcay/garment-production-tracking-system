/**
 * Validates an email address format cleanly without over-rejecting valid addresses.
 *
 * @param {string} email - The email string to validate.
 * @returns {boolean} True if valid, false otherwise.
 */
function isValidEmail(email) {
  if (typeof email !== 'string') return false;

  const trimmed = email.trim();
  if (!trimmed || trimmed.length > 254) return false;

  // Standard practical check: local@domain.tld (no spaces, single @, valid domain labels)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  if (!emailRegex.test(trimmed)) return false;

  const [localPart, domainPart] = trimmed.split('@');

  // Local part max length is 64 octets; disallow consecutive dots or leading/trailing dots
  if (
    localPart.length > 64 ||
    localPart.startsWith('.') ||
    localPart.endsWith('.') ||
    localPart.includes('..')
  ) {
    return false;
  }

  // Domain must have valid dot-separated labels (no leading/trailing hyphens or empty labels)
  const labels = domainPart.split('.');
  if (labels.some((label) => !label || label.length > 63 || /^-|-$/.test(label))) {
    return false;
  }

  return true;
}

// Live input validation helper (optional UI wiring)
function attachEmailValidator(input, options = {}) {
  const inputEl = typeof input === 'string' ? document.querySelector(input) : input;
  if (!inputEl) return () => false;

  const feedbackEl = typeof options.feedbackEl === 'string'
    ? document.querySelector(options.feedbackEl)
    : options.feedbackEl;

  const validMessage = options.validMessage ?? 'Valid email address';
  const invalidMessage = options.invalidMessage ?? 'Please enter a valid email address';

  const validate = () => {
    const raw = inputEl.value;
    if (!raw.trim()) {
      inputEl.classList.remove('is-valid', 'is-invalid');
      if (feedbackEl) {
        feedbackEl.textContent = '';
        feedbackEl.className = 'feedback';
      }
      return false;
    }

    const valid = isValidEmail(raw);
    inputEl.classList.toggle('is-valid', valid);
    inputEl.classList.toggle('is-invalid', !valid);

    if (feedbackEl) {
      feedbackEl.textContent = valid ? validMessage : invalidMessage;
      feedbackEl.className = `feedback ${valid ? 'valid' : 'invalid'}`;
    }

    return valid;
  };

  inputEl.addEventListener('input', validate);
  inputEl.addEventListener('blur', () => {
    inputEl.value = inputEl.value.trim();
    validate();
  });

  if (inputEl.value) validate();
  return validate;
}