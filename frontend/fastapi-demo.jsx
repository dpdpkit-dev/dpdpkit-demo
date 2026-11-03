// Mounts @dpdpkit/react on the FastAPI page. The "Act as" select stands in for a login: the chosen
// fictional user goes to dpdpkit-fastapi in the X-User header (see app/fastapi_demo.py).
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { ConsentNotice, DpdpProvider, LanguageSwitcher, PreferenceCenter, RightsRequestForm } from "@dpdpkit/react";
import "@dpdpkit/react/styles.css";

const root = document.getElementById("fastapi-demo");
const userSelect = document.getElementById("demo-user");
const localeSelect = document.getElementById("demo-locale");

function Demo() {
  const [user, setUser] = useState(userSelect.value);
  const [locale, setLocale] = useState(localeSelect.value);
  userSelect.onchange = () => setUser(userSelect.value);
  localeSelect.onchange = () => setLocale(localeSelect.value);
  // Remount per user and language so each flow starts from what the server holds for that person.
  return (
    <DpdpProvider key={`${user}/${locale}`} options={{ baseUrl: root.dataset.baseUrl, headers: { "X-User": user } }} locale={locale}>
      <h3>Consent notice</h3>
      <ConsentNotice />
      <h3>Preference centre</h3>
      <PreferenceCenter />
      <h3>Rights request</h3>
      <RightsRequestForm />
    </DpdpProvider>
  );
}

createRoot(root).render(<Demo />);
