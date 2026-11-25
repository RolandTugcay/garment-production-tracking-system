function isValidUsername(username) {
    if (typeof username !== "string") return false;

    // 8–15 characters; letters, numbers, hyphens, and dots.
    return /^[A-Za-z0-9](?:[A-Za-z0-9._-]{6,13})[A-Za-z0-9]$/.test(username);
}

function isValidUserPassword(password) {
    if (typeof password !== "string") return false;

    // 8–64 printable ASCII characters, with no whitespace.
    // This includes letters, numbers, and common symbols.
    return /^[!-~]{8,64}$/.test(password);
}

function attachUsernamePasswordValidator(options = {}) {
    const usernameInput = typeof options.usernameInput === "string"
        ? document.querySelector(options.usernameInput)
        : options.usernameInput;

    const passwordInput = typeof options.passwordInput === "string"
        ? document.querySelector(options.passwordInput)
        : options.passwordInput;

    const usernameFeedback = typeof options.usernameFeedback === "string"
        ? document.querySelector(options.usernameFeedback)
        : options.usernameFeedback;

    const passwordFeedback = typeof options.passwordFeedback === "string"
        ? document.querySelector(options.passwordFeedback)
        : options.passwordFeedback;

    const form = options.form
        ? (
            typeof options.form === "string"
                ? document.querySelector(options.form)
                : options.form
        )
        : usernameInput?.form;

    if (!usernameInput || !passwordInput || !form) {
        console.warn("Username/password validator could not find its form fields.");
        return null;
    }

    function showResult(input, feedback, valid, validMessage, invalidMessage) {
        input.classList.toggle("is-valid", valid);
        input.classList.toggle("is-invalid", !valid);

        if (feedback) {
            feedback.textContent = valid ? validMessage : invalidMessage;
            feedback.className = `feedback ${valid ? "valid" : "invalid"}`;
        }
    }

    function clearResult(input, feedback) {
        input.classList.remove("is-valid", "is-invalid");

        if (feedback) {
            feedback.textContent = "";
            feedback.className = "feedback";
        }
    }

    function validateUsername() {
        const value = usernameInput.value;
        const valid = isValidUsername(value);

        showResult(
            usernameInput,
            usernameFeedback,
            valid,
            "Username format is valid.",
            "Use 8–15 characters: letters, numbers, hyphens, underscore and dots. No spaces."
        );

        return valid;
    }

    function validatePassword() {
        const value = passwordInput.value;

        // Password is optional while editing an account.
        if (!value && !passwordInput.required) {
            clearResult(passwordInput, passwordFeedback);
            return true;
        }

        const valid = isValidUserPassword(value);

        showResult(
            passwordInput,
            passwordFeedback,
            valid,
            "Password format is valid.",
            "Use 8–64 characters: Letters, numbers, and symbols are allowed. No spaces"
        );

        return valid;
    }

    function reset() {
        clearResult(usernameInput, usernameFeedback);
        clearResult(passwordInput, passwordFeedback);
    }

    usernameInput.addEventListener("input", validateUsername);
    passwordInput.addEventListener("input", validatePassword);

    form.addEventListener("submit", (event) => {
        const usernameValid = validateUsername();
        const passwordValid = validatePassword();

        if (!usernameValid || !passwordValid) {
            event.preventDefault();

            if (!usernameValid) {
                usernameInput.focus();
            } else {
                passwordInput.focus();
            }
        }
    });

    return {
        validateUsername,
        validatePassword,
        reset,
    };
}