self.addEventListener("push", (event) => {
  event.waitUntil(
    self.registration.showNotification("Gestão de Demandas", {
      body: "Você tem uma nova notificação. Entre na aplicação para consultar as atualizações.",
      icon: "/marca/sebrae-cor.svg",
      badge: "/marca/sebrae-cor.svg",
      data: { path: "/" },
      tag: "gestao-de-demandas-update",
      renotify: false,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => new URL(client.url).origin === self.location.origin);
      if (existing) return existing.focus();
      return self.clients.openWindow(new URL("/", self.location.origin).href);
    }),
  );
});
