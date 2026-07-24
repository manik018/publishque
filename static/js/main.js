document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("mobile-sidebar");
    const openButtons = document.querySelectorAll("[data-sidebar-open]");
    const closeButtons = document.querySelectorAll("[data-sidebar-close]");

    if (!sidebar) {
        return;
    }

    const openSidebar = () => {
        sidebar.classList.remove("hidden");
        sidebar.setAttribute("aria-hidden", "false");
    };

    const closeSidebar = () => {
        sidebar.classList.add("hidden");
        sidebar.setAttribute("aria-hidden", "true");
    };

    openButtons.forEach((button) => button.addEventListener("click", openSidebar));
    closeButtons.forEach((button) => button.addEventListener("click", closeSidebar));

    const dismissToast = (toast) => {
        toast.classList.add("opacity-0", "translate-x-4");
        window.setTimeout(() => toast.remove(), 200);
    };

    document.querySelectorAll(".toast").forEach((toast) => {
        toast.classList.add("transition", "duration-200", "ease-out");
        window.setTimeout(() => dismissToast(toast), 5000);
    });

    document.querySelectorAll(".toast-close").forEach((button) => {
        button.addEventListener("click", () => {
            const toast = button.closest(".toast");
            if (toast) {
                dismissToast(toast);
            }
        });
    });
});
