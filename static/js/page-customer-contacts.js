const customerContactModalSave = document.getElementById(
    "modal-save-customer-contact"
);
const customerContactModalDelete = document.getElementById(
    "modal-delete-customer-contact"
);

if (customerContactModalSave) {
    customerContactModalSave.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;
        if (!button) return;

        const saveForm = document.getElementById("customer-contact-form-save");
        const customerIdInput = document.getElementById(
            "customer-contact-customer-id"
        );
        const customerNameInput = document.getElementById(
            "customer-contact-customer-name"
        );
        const firstNameInput = document.getElementById(
            "customer-contact-first-name"
        );
        const lastNameInput = document.getElementById(
            "customer-contact-last-name"
        );
        const positionInput = document.getElementById(
            "customer-contact-position"
        );
        const phoneInput = document.getElementById("customer-contact-phone");
        const emailInput = document.getElementById("customer-contact-email");
        const isPrimaryInput = document.getElementById(
            "customer-contact-is-primary"
        );
        const title = document.getElementById(
            "modal-save-customer-contact-label"
        );

        if (
            !saveForm ||
            !customerIdInput ||
            !customerNameInput ||
            !firstNameInput ||
            !lastNameInput ||
            !positionInput ||
            !phoneInput ||
            !emailInput ||
            !isPrimaryInput ||
            !title
        ) {
            console.error("Customer-contact modal is missing a required field.");
            return;
        }

        const editUrl = button.dataset.editUrl;

        saveForm.reset();
        customerIdInput.value = button.dataset.customerId || "";
        customerNameInput.value = button.dataset.customerName || "";

        if (editUrl) {
            saveForm.action = editUrl;
            firstNameInput.value = button.dataset.contactFirstName || "";
            lastNameInput.value = button.dataset.contactLastName || "";
            positionInput.value = button.dataset.contactPosition || "";
            phoneInput.value = button.dataset.contactPhone || "";
            emailInput.value = button.dataset.contactEmail || "";
            isPrimaryInput.value = button.dataset.contactIsPrimary || "No";
            title.textContent = "Edit customer contact";
        } else {
            saveForm.action = saveForm.dataset.createUrl;
            isPrimaryInput.value = "No";
            title.textContent = "Add customer contact";
        }
    });
}

if (customerContactModalDelete) {
    customerContactModalDelete.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;
        if (!button) return;

        const deleteForm = document.getElementById(
            "customer-contact-form-delete"
        );
        const deleteMessage = document.getElementById(
            "modal-delete-customer-contact-message"
        );

        if (!deleteForm || !deleteMessage) {
            console.error("Customer-contact delete modal is missing a field.");
            return;
        }

        deleteForm.action = button.dataset.deleteUrl || "#";

        const firstName = button.dataset.contactFirstName || "";
        const lastName = button.dataset.contactLastName || "";
        const contactName = `${firstName} ${lastName}`.trim() || "this contact";
        const customerName = button.dataset.customerName || "the customer";

        deleteMessage.textContent =
            `Are you sure you want to delete ${contactName} from ${customerName}?`;
    });
}


const validatePrimaryPhone = attachPhoneValidator('#customer-contact-phone', {
    feedbackEl: '#phoneFeedback'
});

const validateEmailInput = attachEmailValidator('#customer-contact-email', {
    feedbackEl: '#emailFeedback'
});