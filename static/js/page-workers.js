const workerClassModalSave = document.getElementById("modal-save-worker");
const workerClassModalDel = document.getElementById("modal-delete-worker")
let hireDatePicker;

workerClassModalSave.addEventListener("show.bs.modal", (event) => {
    const button = event.relatedTarget;
    const saveForm = document.getElementById("worker-form-save");
    const workerClassInput = document.getElementById("new-worker-class");
    const firstNameInput = document.getElementById("new-worker-first-name");
    const lastNameInput = document.getElementById("new-worker-last-name");
    const phoneInput = document.getElementById("new-worker-phone");
    const emailInput = document.getElementById("new-worker-email");
    const hireDateInput = document.getElementById("new-worker-hire-date");
    const statusInput = document.getElementById("new-worker-status");
    const addressInput = document.getElementById("new-worker-address");
    const notesInput = document.getElementById("new-worker-notes");
    const title = document.getElementById("modal-save-worker-label");

    const editUrl = button?.dataset.editUrl;

    if (editUrl) {
        saveForm.action = editUrl;
        workerClassInput.value = button.dataset.workerClassId || "";
        firstNameInput.value = button.dataset.workerFirstName || "";
        lastNameInput.value = button.dataset.workerLastName || "";
        phoneInput.value = button.dataset.workerPhone || "";
        emailInput.value = button.dataset.workerEmail || "";
        if (hireDatePicker) {
            hireDatePicker.setDate(button.dataset.workerHireDate || "", false);
        } else {
            hireDateInput.value = button.dataset.workerHireDate || "";
        }
        statusInput.value = button.dataset.workerStatus || "";
        addressInput.value = button.dataset.workerAddress || "";
        notesInput.value = button.dataset.workerNotes || "";
        title.textContent = "Edit worker";
    } else {
        saveForm.action = saveForm.dataset.createUrl;
        saveForm.reset();
        if (hireDatePicker) {
            hireDatePicker.clear();
        }
        
        notesInput.value = ""
        title.textContent = "Add new worker";
    }

});

workerClassModalDel.addEventListener("show.bs.modal", (event) => {
    const deleteButton = event.relatedTarget;
    if (!deleteButton) return;
    const deleteForm = document.getElementById("worker-form-del");
    const deleteMessage = document.getElementById("modal-delete-worker-message");
    const workerFirstName = deleteButton.dataset.workerFirstName || "";
    const workerLastName = deleteButton.dataset.workerLastName || "";

    deleteForm.action = deleteButton.dataset.deleteUrl;
    deleteMessage.textContent = `Are you sure you want to delete ${workerFirstName} ${workerLastName}?`;
});

document.addEventListener('DOMContentLoaded', () => {
    // Flatpickr: date picker
    hireDatePicker = flatpickr('#new-worker-hire-date', {
        dateFormat: 'Y-m-d',
    });
});

const validatePrimaryPhone = attachPhoneValidator('#new-worker-phone', {
    feedbackEl: '#phoneFeedback'
});

const validateEmailInput = attachEmailValidator('#new-worker-email', {
      feedbackEl: '#emailFeedback'
    });
