const customerModalSave = document.getElementById("modal-save-customer");
const customerModalDelete = document.getElementById("modal-delete-customer");

if (customerModalSave) {
    customerModalSave.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;
        if (!button) return;

        const saveForm = document.getElementById("customer-form-save");
        const codeInput = document.getElementById("customer-code");
        const nameInput = document.getElementById("customer-name");
        const statusInput = document.getElementById("customer-status");
        const addressInput = document.getElementById("customer-address");
        const notesInput = document.getElementById("customer-notes");
        const title = document.getElementById("modal-save-customer-label");

        if (
            !saveForm ||
            !codeInput ||
            !nameInput ||
            !statusInput ||
            !addressInput ||
            !notesInput ||
            !title
        ) {
            return;
        }

        const editUrl = button.dataset.editUrl;
        saveForm.reset();

        if (editUrl) {
            saveForm.action = editUrl;
            codeInput.value = button.dataset.customerCode || "";
            nameInput.value = button.dataset.customerName || "";
            statusInput.value = button.dataset.customerStatus || "Active";
            addressInput.value = button.dataset.customerAddress || "";
            notesInput.value = button.dataset.customerNotes || "";
            title.textContent = "Edit customer";

            codeInput.readOnly = true;
            codeInput.disabled = true;
        } else {
            saveForm.action = saveForm.dataset.createUrl;
            statusInput.value = "Active";
            title.textContent = "Add customer";

            codeInput.readOnly = false;
            codeInput.required = true;
            codeInput.disabled = false;

            addressInput.value = "";
            notesInput.value = "";
        }
    });
}

if (customerModalDelete) {
    customerModalDelete.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;
        if (!button) return;

        const deleteForm = document.getElementById("customer-form-delete");
        const deleteMessage = document.getElementById(
            "modal-delete-customer-message"
        );

        if (!deleteForm || !deleteMessage) return;

        deleteForm.action = button.dataset.deleteUrl || "#";
        const customerName = button.dataset.customerName || "this customer";
        deleteMessage.textContent =
            `Are you sure you want to delete ${customerName}?`;
    });
}
