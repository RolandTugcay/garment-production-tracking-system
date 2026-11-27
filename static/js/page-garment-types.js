const garmentTypeModalSave = document.getElementById("modal-save-garment-type");
const garmentTypeModalDel = document.getElementById("modal-delete-garment-type")

garmentTypeModalSave.addEventListener("show.bs.modal", (event) => {
    const button = event.relatedTarget;
    const saveForm = document.getElementById("garment-type-form-save");
    const codeInput = document.getElementById("new-garment-type-code");
    const nameInput = document.getElementById("new-garment-type-name");
    const descriptionInput = document.getElementById("new-garment-type-description");
    const statusInput = document.getElementById("new-garment-type-status");
    const title = document.getElementById("modal-save-garment-type-label");

    const editUrl = button?.dataset.editUrl;

    if (editUrl) {
        saveForm.action = editUrl;
        codeInput.value = button.dataset.garmentTypeCode || "";
        codeInput.readOnly = true;
        codeInput.disabled = true;

        nameInput.value = button.dataset.garmentTypeName || "";
        descriptionInput.value =button.dataset.garmentTypeDescription || "";
        statusInput.value = button.dataset.garmentTypeStatus || "";
        title.textContent = "Edit garment type";
    } else {
        saveForm.action = saveForm.dataset.createUrl;
        saveForm.reset();

        codeInput.readOnly = false;
        codeInput.required = true;
        codeInput.disabled = false;
        descriptionInput.value = "";
        title.textContent = "Add new garment type";
    }

});

garmentTypeModalDel.addEventListener("show.bs.modal", (event) => {
    const deleteButton = event.relatedTarget;
    if (!deleteButton) return;
        const deleteForm = document.getElementById("garment-type-form-del");
        const deleteMessage = document.getElementById("modal-delete-garment-type-message"
    );

    const garmentTypeId = deleteButton.dataset.garmentTypeId;
    const garmentTypeName = deleteButton.dataset.garmentTypeName || "this garment type";

    deleteForm.action = deleteButton.dataset.deleteUrl;
    deleteMessage.textContent = `Are you sure you want to delete ${garmentTypeName}?`;
});