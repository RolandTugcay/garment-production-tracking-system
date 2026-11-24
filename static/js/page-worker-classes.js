const workerClassModalSave = document.getElementById("modal-save-worker-class");
const workerClassModalDel = document.getElementById("modal-delete-worker-class")

workerClassModalSave.addEventListener("show.bs.modal", (event) => {
    const button = event.relatedTarget;
    const saveForm = document.getElementById("worker-class-form-save");
    const codeInput = document.getElementById("new-worker-class-code");
    const nameInput = document.getElementById("new-worker-class-name");
    const descriptionInput = document.getElementById("new-worker-class-description");
    const statusInput = document.getElementById("new-worker-class-status");
    const title = document.getElementById("modal-save-worker-class-label");

    const editUrl = button?.dataset.editUrl;

    if (editUrl) {
        saveForm.action = editUrl;
        codeInput.value = button.dataset.workerClassCode || "";
        codeInput.readOnly = true;
        codeInput.disabled = true;

        nameInput.value = button.dataset.workerClassName || "";
        descriptionInput.value =button.dataset.workerClassDescription || "";
        statusInput.value = button.dataset.workerClassStatus || "";
        title.textContent = "Edit worker class";
    } else {
        saveForm.action = saveForm.dataset.createUrl;
        saveForm.reset();

        codeInput.readOnly = false;
        codeInput.required = true;
        codeInput.disabled = false;
        descriptionInput.value = "";
        title.textContent = "Add new worker class";
    }

});

workerClassModalDel.addEventListener("show.bs.modal", (event) => {
    const deleteButton = event.relatedTarget;
    if (!deleteButton) return;
        const deleteForm = document.getElementById("worker-class-form-del");
        const deleteMessage = document.getElementById("modal-delete-worker-class-message"
    );

    const workerClassId = deleteButton.dataset.workerClassId;
    const workerClassName = deleteButton.dataset.workerClassName || "this worker class";

    deleteForm.action = deleteButton.dataset.deleteUrl;
    deleteMessage.textContent = `Are you sure you want to delete ${workerClassName}?`;
});