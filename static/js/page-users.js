const userModalSave = document.getElementById("modal-save-user");
const userModalDelete = document.getElementById("modal-delete-user");

if (userModalSave) {
    userModalSave.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;
        if (!button) return;

        const saveForm = document.getElementById("user-form-save");
        const workerInput = document.getElementById("new-worker");
        const usernameInput = document.getElementById("new-user-username");
        const passwordInput = document.getElementById("new-user-password");
        const passwordLb = document.getElementById("lb-new-user-password");
        const roleInput = document.getElementById("new-user-role");
        const statusInput = document.getElementById("new-user-status");
        const title = document.getElementById("modal-save-user-label");

        if (
            !saveForm ||
            !workerInput ||
            !usernameInput ||
            !passwordInput ||
            !roleInput ||
            !statusInput ||
            !title
        ) {
            return;
        }

        const editUrl = button.dataset.editUrl;

        saveForm.reset();
        passwordInput.disabled = false;
        passwordInput.readOnly = false;
        passwordInput.hidden = false;
        passwordLb.hidden = false;
        passwordInput.value = "";

        if (editUrl) {
            saveForm.action = editUrl;
            workerInput.value = button.dataset.userWorkerId || "";
            usernameInput.value = button.dataset.userUsername || "";
            roleInput.value = button.dataset.userRole || "";
            statusInput.value = button.dataset.userStatus || "";

            passwordInput.required = false;
            passwordInput.hidden = true;
            passwordLb.hidden = true;
            title.textContent = "Edit user";
        } else {
            saveForm.action = saveForm.dataset.createUrl;
            title.textContent = "Add new user";

            passwordInput.required = true;
            passwordInput.hidden = false;
            passwordLb.hidden = false;
            roleInput.value = "User";
            statusInput.value = "Active";
        }

        userCredentialsValidator?.reset();
    });
}

if (userModalDelete) {
    userModalDelete.addEventListener("show.bs.modal", (event) => {
        const deleteButton = event.relatedTarget;
        if (!deleteButton) return;

        const deleteForm = document.getElementById("user-form-del");
        const deleteMessage = document.getElementById(
            "modal-delete-user-message"
        );

        if (!deleteForm || !deleteMessage) return;

        deleteForm.action = deleteButton.dataset.deleteUrl || "#";

        const username = deleteButton.dataset.userUsername || "this user";
        deleteMessage.textContent =
            `Are you sure you want to delete ${username}?`;
    });
}

const userCredentialsValidator = attachUsernamePasswordValidator({
    form: "#user-form-save",
    usernameInput: "#new-user-username",
    usernameFeedback: "#usernameFeedback",
    passwordInput: "#new-user-password",
    passwordFeedback: "#passwordFeedback",
});