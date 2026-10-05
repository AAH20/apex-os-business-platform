import { useState } from 'react';

type Step =
  | "welcome"
  | "organization"
  | "modules"
  | "scale"
  | "deployment"
  | "team"
  | "integrations"
  | "review";

interface TeamMember {
  email: string;
  role: string;
}

interface WizardData {
  orgName: string;
  industry: string;
  orgSize: string;
  modules: string[];
  scale: string;
  deployment: string;
  team: TeamMember[];
  integrations: string[];
}

const STEPS: { key: Step; label: string }[] = [
  { key: "welcome", label: "Welcome" },
  { key: "organization", label: "Organization" },
  { key: "modules", label: "Modules" },
  { key: "scale", label: "Scale" },
  { key: "deployment", label: "Deployment" },
  { key: "team", label: "Team" },
  { key: "integrations", label: "Integrations" },
  { key: "review", label: "Review" },
];

const MODULES = [
  { id: "analytics", label: "Analytics & Reporting", desc: "Dashboards, KPIs, and insights" },
  { id: "crm", label: "CRM", desc: "Customer relationship management" },
  { id: "projects", label: "Project Management", desc: "Tasks, timelines, and collaboration" },
  { id: "finance", label: "Finance & Billing", desc: "Invoicing, expenses, and budgets" },
  { id: "hr", label: "HR & People", desc: "Employee records and payroll" },
  { id: "inventory", label: "Inventory", desc: "Stock tracking and supply chain" },
  { id: "support", label: "Support Desk", desc: "Ticketing and customer support" },
  { id: "automation", label: "Automation", desc: "Workflows and process automation" },
];

const SCALES = [
  { id: "startup", label: "Startup", range: "1–10 employees" },
  { id: "smb", label: "SMB", range: "11–100 employees" },
  { id: "enterprise", label: "Enterprise", range: "101–1,000 employees" },
  { id: "large-enterprise", label: "Large Enterprise", range: "1,000+ employees" },
];

const DEPLOYMENTS = [
  { id: "cloud", label: "Cloud", desc: "Fully managed SaaS, no infrastructure needed" },
  { id: "on-premise", label: "On-Premise", desc: "Self-hosted on your own servers" },
  { id: "hybrid", label: "Hybrid", desc: "Mix of cloud and on-premise" },
];

const INTEGRATIONS = [
  { id: "slack", label: "Slack", desc: "Notifications and commands in Slack" },
  { id: "teams", label: "Microsoft Teams", desc: "Collaboration within Teams" },
  { id: "email", label: "Email", desc: "Email notifications and digests" },
  { id: "api", label: "REST API", desc: "Custom integrations via API" },
];

const ROLES = ["Admin", "Manager", "Member", "Viewer"];

const INDUSTRIES = [
  "Technology", "Healthcare", "Finance", "Retail", "Manufacturing",
  "Education", "Real Estate", "Consulting", "Other",
];

export default function OnboardingWizard() {
  const [step, setStep] = useState<Step>("welcome");
  const [data, setData] = useState<WizardData>({
    orgName: "",
    industry: "",
    orgSize: "",
    modules: [],
    scale: "",
    deployment: "",
    team: [],
    integrations: [],
  });
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("Member");

  const stepIndex = STEPS.findIndex((s) => s.key === step);

  const next = () => {
    const idx = STEPS.findIndex((s) => s.key === step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1].key);
  };

  const prev = () => {
    const idx = STEPS.findIndex((s) => s.key === step);
    if (idx > 0) setStep(STEPS[idx - 1].key);
  };

  const skip = () => setStep("review");

  const toggleModule = (id: string) => {
    setData((d) => ({
      ...d,
      modules: d.modules.includes(id)
        ? d.modules.filter((m) => m !== id)
        : [...d.modules, id],
    }));
  };

  const toggleIntegration = (id: string) => {
    setData((d) => ({
      ...d,
      integrations: d.integrations.includes(id)
        ? d.integrations.filter((i) => i !== id)
        : [...d.integrations, id],
    }));
  };

  const addMember = () => {
    if (!newEmail.trim()) return;
    setData((d) => ({
      ...d,
      team: [...d.team, { email: newEmail.trim(), role: newRole }],
    }));
    setNewEmail("");
    setNewRole("Member");
  };

  const removeMember = (idx: number) => {
    setData((d) => ({
      ...d,
      team: d.team.filter((_, i) => i !== idx),
    }));
  };

  const canProceed = () => {
    switch (step) {
      case "organization":
        return data.orgName.trim() !== "" && data.industry !== "";
      case "modules":
        return data.modules.length > 0;
      case "scale":
        return data.scale !== "";
      case "deployment":
        return data.deployment !== "";
      default:
        return true;
    }
  };

  const renderStep = () => {
    switch (step) {
      case "welcome":
        return (
          <div className="text-center py-8">
            <h1 className="text-3xl font-bold text-gray-100 mb-4">
              Welcome to APEX-OS
            </h1>
            <p className="text-gray-400 text-lg mb-8 max-w-xl mx-auto">
              Your all-in-one business platform. Let's get you set up in a few
              quick steps — it takes less than 2 minutes.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto mb-8">
              {[
                { icon: "🏢", title: "Organization", desc: "Tell us about your company" },
                { icon: "🧩", title: "Modules", desc: "Pick the tools you need" },
                { icon: "🚀", title: "Launch", desc: "Deploy and invite your team" },
              ].map((c) => (
                <div key={c.title} className="bg-gray-800 rounded-lg p-4">
                  <div className="text-3xl mb-2">{c.icon}</div>
                  <h3 className="text-gray-100 font-semibold">{c.title}</h3>
                  <p className="text-gray-400 text-sm">{c.desc}</p>
                </div>
              ))}
            </div>
          </div>
        );

      case "organization":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Organization Profile
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Organization Name
                </label>
                <input
                  type="text"
                  value={data.orgName}
                  onChange={(e) => setData({ ...data, orgName: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                  placeholder="Acme Corp"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Industry
                </label>
                <select
                  value={data.industry}
                  onChange={(e) => setData({ ...data, industry: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                >
                  <option value="">Select industry</option>
                  {INDUSTRIES.map((ind) => (
                    <option key={ind} value={ind}>
                      {ind}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Company Size
                </label>
                <input
                  type="text"
                  value={data.orgSize}
                  onChange={(e) => setData({ ...data, orgSize: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                  placeholder="e.g., 50 employees"
                />
              </div>
            </div>
          </div>
        );

      case "modules":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Select Modules
            </h2>
            <p className="text-gray-400 mb-4">
              Choose the modules you want to enable. You can change this later.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {MODULES.map((mod) => (
                <button
                  key={mod.id}
                  onClick={() => toggleModule(mod.id)}
                  className={`text-left p-4 rounded-lg border transition-colors ${
                    data.modules.includes(mod.id)
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-gray-700 bg-gray-800 hover:border-gray-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-gray-100 font-medium">{mod.label}</span>
                    <span
                      className={`w-5 h-5 rounded border flex items-center justify-center text-xs ${
                        data.modules.includes(mod.id)
                          ? "bg-blue-500 border-blue-500 text-white"
                          : "border-gray-600"
                      }`}
                    >
                      {data.modules.includes(mod.id) && "✓"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mt-1">{mod.desc}</p>
                </button>
              ))}
            </div>
          </div>
        );

      case "scale":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Select Scale
            </h2>
            <p className="text-gray-400 mb-4">
              This helps us recommend the right plan and resources.
            </p>
            <div className="space-y-3">
              {SCALES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setData({ ...data, scale: s.id })}
                  className={`w-full text-left p-4 rounded-lg border transition-colors ${
                    data.scale === s.id
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-gray-700 bg-gray-800 hover:border-gray-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-gray-100 font-medium">{s.label}</span>
                      <span className="text-gray-400 ml-3 text-sm">{s.range}</span>
                    </div>
                    <span
                      className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                        data.scale === s.id
                          ? "border-blue-500 bg-blue-500"
                          : "border-gray-600"
                      }`}
                    >
                      {data.scale === s.id && (
                        <span className="w-2 h-2 bg-gray-900 rounded-full" />
                      )}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        );

      case "deployment":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Deployment Preference
            </h2>
            <p className="text-gray-400 mb-4">
              How would you like to deploy APEX-OS?
            </p>
            <div className="space-y-3">
              {DEPLOYMENTS.map((dep) => (
                <button
                  key={dep.id}
                  onClick={() => setData({ ...data, deployment: dep.id })}
                  className={`w-full text-left p-4 rounded-lg border transition-colors ${
                    data.deployment === dep.id
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-gray-700 bg-gray-800 hover:border-gray-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-gray-100 font-medium">{dep.label}</span>
                      <p className="text-gray-400 text-sm mt-1">{dep.desc}</p>
                    </div>
                    <span
                      className={`w-5 h-5 rounded-full border flex items-center justify-center ${
                        data.deployment === dep.id
                          ? "border-blue-500 bg-blue-500"
                          : "border-gray-600"
                      }`}
                    >
                      {data.deployment === dep.id && (
                        <span className="w-2 h-2 bg-gray-900 rounded-full" />
                      )}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        );

      case "team":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Team Setup
            </h2>
            <p className="text-gray-400 mb-4">
              Invite team members and assign roles.
            </p>
            <div className="flex gap-2 mb-4">
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
                placeholder="teammate@company.com"
                onKeyDown={(e) => e.key === "Enter" && addMember()}
              />
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:border-blue-500"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
              <button
                onClick={addMember}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Add
              </button>
            </div>
            {data.team.length > 0 && (
              <div className="space-y-2">
                {data.team.map((member, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2"
                  >
                    <span className="text-gray-100">{member.email}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-400 text-sm">{member.role}</span>
                      <button
                        onClick={() => removeMember(idx)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "integrations":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Integrations
            </h2>
            <p className="text-gray-400 mb-4">
              Connect your favorite tools. You can set these up later too.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {INTEGRATIONS.map((intg) => (
                <button
                  key={intg.id}
                  onClick={() => toggleIntegration(intg.id)}
                  className={`text-left p-4 rounded-lg border transition-colors ${
                    data.integrations.includes(intg.id)
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-gray-700 bg-gray-800 hover:border-gray-600"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-gray-100 font-medium">{intg.label}</span>
                    <span
                      className={`w-5 h-5 rounded border flex items-center justify-center text-xs ${
                        data.integrations.includes(intg.id)
                          ? "bg-blue-500 border-blue-500 text-white"
                          : "border-gray-600"
                      }`}
                    >
                      {data.integrations.includes(intg.id) && "✓"}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mt-1">{intg.desc}</p>
                </button>
              ))}
            </div>
          </div>
        );

      case "review":
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-100 mb-6">
              Review & Confirm
            </h2>
            <div className="space-y-4">
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-gray-300 font-semibold mb-2">Organization</h3>
                <p className="text-gray-100">{data.orgName || "—"}</p>
                <p className="text-gray-400 text-sm">
                  {data.industry} {data.orgSize && `· ${data.orgSize}`}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-gray-300 font-semibold mb-2">Modules</h3>
                <div className="flex flex-wrap gap-2">
                  {data.modules.map((m) => (
                    <span
                      key={m}
                      className="px-2 py-1 bg-gray-700 rounded text-gray-200 text-sm"
                    >
                      {MODULES.find((mod) => mod.id === m)?.label || m}
                    </span>
                  ))}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-gray-300 font-semibold mb-2">Scale</h3>
                <p className="text-gray-100">
                  {SCALES.find((s) => s.id === data.scale)?.label || "—"}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-gray-300 font-semibold mb-2">Deployment</h3>
                <p className="text-gray-100">
                  {DEPLOYMENTS.find((d) => d.id === data.deployment)?.label || "—"}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-gray-300 font-semibold mb-2">
                  Team ({data.team.length})
                </h3>
                {data.team.length > 0 ? (
                  <ul className="space-y-1">
                    {data.team.map((m, i) => (
                      <li key={i} className="text-gray-400 text-sm">
                        {m.email} — {m.role}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-400 text-sm">No members added</p>
                )}
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-gray-300 font-semibold mb-2">Integrations</h3>
                {data.integrations.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {data.integrations.map((i) => (
                      <span
                        key={i}
                        className="px-2 py-1 bg-gray-700 rounded text-gray-200 text-sm"
                      >
                        {INTEGRATIONS.find((intg) => intg.id === i)?.label || i}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm">No integrations selected</p>
                )}
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Progress bar */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-3xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">
              Step {stepIndex + 1} of {STEPS.length}
            </span>
            <button
              onClick={skip}
              className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Skip setup
            </button>
          </div>
          <div className="flex gap-1">
            {STEPS.map((s, i) => (
              <div
                key={s.key}
                className={`h-1 flex-1 rounded-full transition-colors ${
                  i <= stepIndex ? "bg-blue-500" : "bg-gray-700"
                }`}
              />
            ))}
          </div>
          <div className="flex justify-between mt-2">
            {STEPS.map((s, i) => (
              <span
                key={s.key}
                className={`text-xs ${
                  i === stepIndex
                    ? "text-blue-400 font-medium"
                    : i < stepIndex
                    ? "text-gray-400"
                    : "text-gray-400"
                }`}
              >
                {s.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Step content */}
      <div className="max-w-3xl mx-auto px-4 py-8">{renderStep()}</div>

      {/* Navigation */}
      <div className="max-w-3xl mx-auto px-4 pb-8">
        <div className="flex items-center justify-between">
          <button
            onClick={prev}
            disabled={stepIndex === 0}
            className="px-4 py-2 rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Back
          </button>
          {step === "review" ? (
            <button
              onClick={() => alert("Onboarding complete! Welcome to APEX-OS.")}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Complete Setup
            </button>
          ) : (
            <button
              onClick={next}
              disabled={!canProceed()}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Continue
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
