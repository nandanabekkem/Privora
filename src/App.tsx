import { FormEvent, ReactNode, useEffect, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { apiGet, apiPost } from "./api"

type View = "home" | "login" | "signup" | "onboarding" | "dashboard"

type DataMapResponse = {
  user_id: number
  account_count: number
  accounts: {
    account_id: number
    service: string
    website: string | null
    status: string
    last_activity: string | null
    data_records: {
      category: string
      description: string | null
    }[]
    data_record_count: number
  }[]
}

type AuditLogsResponse = {
  user_id: number
  count: number
  logs: {
    id: number
    privacy_action_id: number | null
    event_type: string
    details: string
    created_at: string
  }[]
}


type PrivacyActionsResponse = {
  user_id: number
  count: number
  actions: {
    id: number
    account_id: number
    action_type: string
    description: string
    status: string
    requires_approval: boolean
    created_at: string
    reviewed_at: string | null
  }[]
}


type RulesResponse = {
  user_id: number
  days_threshold: number
  saved_policy_count: number
  account_count: number
  recommendation_count: number
  recommendations: {
    account_id: number
    service: string
    recommendation: "KEEP" | "REVIEW"
    reason: string
    days_threshold: number
    applied_policy_count: number
    requires_user_approval: boolean
  }[]
  note: string
}

type Recommendation = {
  id: number
  accountId: number
  actionId: number | null
  status: string
  title: string
  account: string
  why: string
  next: string
}


type CreateActionResponse = {
  id: number
  user_id: number
  account_id: number
  action_type: string
  description: string
  status: string
  requires_approval: boolean
  created_at: string
  message: string
}


const Arrow = ({ diagonal = false }: { diagonal?: boolean }) => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d={diagonal ? "M5 19 19 5M9 5h10v10" : "M5 12h14M13 6l6 6-6 6"} />
  </svg>
)

const Mark = ({ small = false }: { small?: boolean }) => (
  <span className={`mark ${small ? "mark--small" : ""}`} aria-hidden="true">
    <i />
    <i />
    <i />
    <i />
  </span>
)

const Label = ({ children }: { children: ReactNode }) => (
  <div className="eyebrow">
    <span>●</span>
    {children}
  </div>
)

const Button = ({
  children,
  onClick,
  kind = "primary",
  type = "button",
}: {
  children: ReactNode
  onClick?: () => void
  kind?: "primary" | "ghost" | "line"
  type?: "button" | "submit"
}) => (
  <button className={`button button--${kind}`} onClick={onClick} type={type}>
    <span>{children}</span>
    <Arrow diagonal={kind !== "ghost"} />
  </button>
)

const GridArt = ({
  type,
}: {
  type: "discover" | "classify" | "recommend" | "act"
}) => {
  const patterns = {
    discover: ["00100", "01110", "11011", "11111", "01010"],
    classify: ["10101", "01110", "11011", "01110", "10101"],
    recommend: ["00100", "10101", "01110", "00100", "01010"],
    act: ["10001", "01010", "00100", "01010", "10001"],
  }
  return (
    <div className="pixel-art" aria-hidden="true">
      {patterns[type]
        .join("")
        .split("")
        .map((cell, i) => (
          <motion.i
            key={i}
            className={cell === "1" ? "on" : ""}
            animate={cell === "1" ? { opacity: [0.35, 1, 0.35] } : undefined}
            transition={{ duration: 2.4, delay: i * 0.04, repeat: Infinity }}
          />
        ))}
    </div>
  )
}

const Guardian = () => (
  <div className="guardian" aria-label="Cinematic animated AI privacy guardian">
    <div className="guardian__particles" aria-hidden="true">
      {Array.from({ length: 18 }, (_, i) => (
        <i key={i} />
      ))}
    </div>
    <div className="guardian__orbit guardian__orbit--one">
      <i />
    </div>
    <div className="guardian__orbit guardian__orbit--two">
      <i />
    </div>
    <div className="guardian__core">
      <span className="guardian__shine" />
      <div className="guardian__face">
        <i />
        <i />
      </div>
    </div>
    <span className="guardian__tag guardian__tag--top">IDENTITY / 01</span>
    <span className="guardian__tag guardian__tag--bottom">ENCRYPTED</span>
    <div className="guardian__scan" />
  </div>
)

const Header = ({
  view,
  navigate,
}: {
  view: View
  navigate: (view: View) => void
}) => {
  const [open, setOpen] = useState(false)
  const go = (next: View, anchor?: string) => {
    navigate(next)
    setOpen(false)
    if (anchor)
      setTimeout(
        () =>
          document
            .getElementById(anchor)
            ?.scrollIntoView({ behavior: "smooth" }),
        50,
      )
  }
  return (
    <header className="header">
      <button
        className="brand"
        onClick={() => go("home")}
        aria-label="Privora home"
      >
        <Mark small />
        <span>PRIVORA</span>
      </button>
      <button
        className="menu-toggle"
        onClick={() => setOpen(!open)}
        aria-label="Toggle menu"
      >
        <i />
        <i />
      </button>
      <nav className={open ? "nav nav--open" : "nav"}>
        <button onClick={() => go("home")}>Home</button>
        <button onClick={() => go("home", "features")}>Features</button>
        <button onClick={() => go("home", "process")}>How it works</button>
        <button onClick={() => go("home", "faq")}>FAQ</button>
      </nav>
      <div className="header__actions">
        {view === "dashboard" ? (
          <button className="avatar" onClick={() => navigate("home")}>
            SK
          </button>
        ) : (
          <>
            <button className="login-link" onClick={() => navigate("login")}>
              Log in
            </button>
            <button className="signup-link" onClick={() => navigate("signup")}>
              Get started <Arrow diagonal />
            </button>
          </>
        )}
      </div>
    </header>
  )
}

const Reveal = ({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) => {
  const reduced = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y: 44 }}
      whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}

const Landing = ({ navigate }: { navigate: (view: View) => void }) => {
  const features = [
    {
      no: "01",
      type: "discover" as const,
      title: "Discover your digital footprint.",
      text: "Keep track of accounts from internships, job applications, courses, hackathons, events, and communities using the information you choose to provide.",
      stat: "DIGITAL FOOTPRINT",
    },
    {
      no: "02",
      type: "classify" as const,
      title: "Understand what you shared.",
      text: "Review potentially shared email addresses, phone numbers, resumes, profile details, and uploaded documents in one organised view.",
      stat: "SHARED INFORMATION",
    },
    {
      no: "03",
      type: "recommend" as const,
      title: "AI privacy intelligence.",
      text: "Turn dense privacy policies and relevant data-handling practices into understandable, plain-language explanations.",
      stat: "AI EXPLANATIONS",
    },
    {
      no: "04",
      type: "act" as const,
      title: "Recommendations, not blind automation.",
      text: "Consider clear recommendations and possible next steps. Consequential actions always wait for your explicit approval.",
      stat: "INFORMED DECISIONS",
    },
    {
      no: "05",
      type: "discover" as const,
      title: "Your decisions, your control.",
      text: "See accounts, recommendations, decisions, and activity history together in one transparent workspace.",
      stat: "ONE CONTROL CENTRE",
    },
  ]
  return (
    <>
      <main>
        <section className="hero">
          <div className="hero__matrix" aria-hidden="true" />
          <div className="hero__topline">
            <Label>AI PRIVACY, ON YOUR TERMS</Label>
            <span>SYS / PROTECTED</span>
          </div>
          <div className="hero__copy">
            <motion.h1
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
            >
              <span>YOUR DIGITAL LIFE.</span>
              <span>
                YOUR <em>CONTROL.</em>
              </span>
            </motion.h1>
            <p>
              Discover forgotten accounts. Understand your digital footprint.
              Make informed decisions about your personal data — with AI that
              keeps you in control.
            </p>
            <div className="hero__buttons">
              <Button onClick={() => navigate("signup")}>Get started</Button>
              <Button
                kind="ghost"
                onClick={() =>
                  document
                    .getElementById("process")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
              >
                Explore Privora
              </Button>
            </div>
          </div>
          <div className="hero__visual">
            <Guardian />
          </div>
          <div className="hero__index">
            <span>PRIVACY INTELLIGENCE</span>
            <span>SCROLL TO EXPLORE ↓</span>
          </div>
        </section>

        <section className="statement">
          <Reveal>
            <Label>YOUR DIGITAL FOOTPRINT, MADE VISIBLE</Label>
            <h2>
              YOUR DATA IS EVERYWHERE.
              <br />
              <span>TAKE BACK CONTROL.</span>
            </h2>
            <div className="statement__aside">
              <span>01—05</span>
              <p>
                No dark patterns. No silent actions. Just focused intelligence
                that puts you back in control.
              </p>
            </div>
          </Reveal>
        </section>

        <section className="features" id="features">
          {features.map((feature, index) => (
            <Reveal className="feature" key={feature.no}>
              <div className="feature__ticker" aria-hidden="true">
                <span>
                  {feature.stat} — {feature.stat} — {feature.stat} —
                </span>
              </div>
              <div className="feature__number">({feature.no})</div>
              <motion.div
                className="feature__art"
                initial={{ opacity: 0, x: index % 2 === 0 ? -80 : 80 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-15%" }}
                transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
              >
                <GridArt type={feature.type} />
              </motion.div>
              <motion.div
                className="feature__content"
                initial={{ opacity: 0, x: index % 2 === 0 ? 100 : -100 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-15%" }}
                transition={{
                  duration: 0.95,
                  delay: 0.08,
                  ease: [0.22, 1, 0.36, 1],
                }}
              >
                <span className="feature__label">{feature.stat}</span>
                <h3>{feature.title}</h3>
                <p>{feature.text}</p>
              </motion.div>
              <button
                className="round-arrow"
                aria-label={`Learn about ${feature.stat}`}
              >
                <Arrow diagonal />
              </button>
            </Reveal>
          ))}
        </section>

        <section className="process" id="process">
          <Reveal className="process__intro">
            <Label>HOW IT WORKS</Label>
            <h2>
              PRIVACY, MADE
              <br />
              UNDERSTANDABLE.
            </h2>
            <p>
              From discovery to action in four transparent steps. Nothing
              happens without you.
            </p>
          </Reveal>
          <motion.div
            className="process__steps"
            animate={{ x: ["0%", "-58%"] }}
            transition={{
              duration: 28,
              repeat: Infinity,
              repeatType: "mirror",
              ease: "linear",
            }}
          >
            {[
              [
                "01",
                "DISCOVER",
                "Add or identify online accounts you want to review. Coverage depends on the information and integrations available.",
              ],
              [
                "02",
                "UNDERSTAND",
                "Examine potentially shared data and relevant privacy information.",
              ],
              [
                "03",
                "REVIEW",
                "Receive AI-assisted explanations and recommendations in plain language.",
              ],
              [
                "04",
                "DECIDE",
                "Choose which actions to approve and transparently track their status.",
              ],
            ].map(([no, title, text], i) => (
              <Reveal className="process-card" key={no}>
                <div className="process-card__meta">
                  <span>STEP / {no}</span>
                  <span>PRIVORA PROTOCOL</span>
                </div>
                <strong className="process-card__index">{no}</strong>
                <h3>{title}</h3>
                <p>{text}</p>
                <div className={`process-card__motion signal--${i + 1}`}>
                  <span>YOUR DECISION</span>
                  <i />
                  <span>YOUR CONTROL</span>
                </div>
              </Reveal>
            ))}
          </motion.div>
        </section>

        <section className="security-band">
          <div className="security-band__marquee">
            <span>
              BUILT FOR CONTROL — DESIGNED FOR TRUST — YOUR APPROVAL, ALWAYS —{" "}
            </span>
            <span aria-hidden="true">
              BUILT FOR CONTROL — DESIGNED FOR TRUST — YOUR APPROVAL, ALWAYS —{" "}
            </span>
          </div>
        </section>

        <section className="faq" id="faq">
          <Reveal className="faq__title">
            <Label>COMMON QUESTIONS</Label>
            <h2>NO FINE PRINT.</h2>
          </Reveal>
          <div className="faq__list">
            {[
              [
                "What is Privora?",
                "Privora is an AI-assisted personal data lifecycle agent that helps you understand and manage the digital footprint information you choose to provide.",
              ],
              [
                "How does it help review forgotten accounts?",
                "Privora organises account details you add and can use available integrations to help identify review candidates. It does not claim to search the entire internet.",
              ],
              [
                "Does it automatically delete accounts?",
                "No. Privora explains options and can prepare next steps, but it never treats a recommendation as an executed deletion.",
              ],
              [
                "What happens before an action is taken?",
                "Consequential actions require your explicit approval. Statuses distinguish proposed, approved, attempted, and confirmed complete.",
              ],
              [
                "Can Privora guarantee every account will be found?",
                "No. Coverage depends on the information you provide and the integrations available to the product.",
              ],
              [
                "How are recommendations presented?",
                "Each recommendation includes a plain-language explanation, why it may matter, possible next steps, and a clear current status.",
              ],
            ].map(([q, a]) => (
              <FaqItem question={q} answer={a} key={q} />
            ))}
          </div>
        </section>

        <section className="final-cta">
          <div className="final-cta__grid" />
          <Reveal>
            <Mark />
            <h2>
              YOUR DIGITAL LIFE.
              <br />
              <span>YOUR DECISIONS.</span>
            </h2>
            <Button onClick={() => navigate("signup")}>
              Get started with Privora
            </Button>
          </Reveal>
        </section>
      </main>
      <Footer navigate={navigate} />
    </>
  )
}

const FaqItem = ({ question, answer }: { question: string; answer: string }) => {
  const [open, setOpen] = useState(false)
  return (
    <div className={`faq-item ${open ? "faq-item--open" : ""}`}>
      <button onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>{question}</span>
        <i>{open ? "−" : "+"}</i>
      </button>
      <AnimatePresence>
        {open && (
          <motion.p
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            {answer}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  )
}

const Footer = ({ navigate }: { navigate: (view: View) => void }) => (
  <footer className="footer">
    <div className="brand">
      <Mark small />
      <span>PRIVORA</span>
    </div>
    <p>
      AI-assisted digital footprint intelligence.
      <br />
      Your digital life. Your decisions.
    </p>
    <div>
      <button onClick={() => navigate("login")}>Log in</button>
      <button onClick={() => navigate("signup")}>Create account</button>
    </div>
    <span>© 2025 PRIVORA / DEMO</span>
  </footer>
)

const Auth = ({
  mode,
  navigate,
}: {
  mode: "login" | "signup"
  navigate: (view: View) => void
}) => {
  const signup = mode === "signup"
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const submit = (e: FormEvent) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget as HTMLFormElement)
    const next: Record<string, string> = {}
    const name = String(form.get("name") || "")
    const email = String(form.get("email") || "")
    const password = String(form.get("password") || "")
    if (signup && name.trim().length < 2) next.name = "Enter your full name."
    if (!email.includes("@")) next.email = "Enter a valid email address."
    if (password.length < 8)
      next.password = "Password must be at least 8 characters."
    if (signup && password !== String(form.get("confirm") || "")) {
      next.confirm = "Passwords do not match."
    }
    if (signup && !form.get("terms"))
      next.terms = "Accept the terms to continue."
    setErrors(next)
    if (Object.keys(next).length) return
    navigate(signup ? "onboarding" : "dashboard")
  }
  return (
    <main className="auth">
      <div className="auth__visual">
        <div className="auth__matrix" />
        <Label>SECURE ACCESS</Label>
        <h1>
          {signup ? (
            <>
              YOUR PRIVACY
              <br />
              STARTS <em>HERE.</em>
            </>
          ) : (
            <>
              WELCOME
              <br />
              <em>BACK.</em>
            </>
          )}
        </h1>
        <div className="auth__guardian">
          <Guardian />
        </div>
        <p>
          Encrypted by design.
          <br />
          Controlled by you.
        </p>
      </div>
      <motion.div
        className="auth__form"
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <span className="auth__step">
          {signup ? "NEW IDENTITY / 01" : "AUTH / VERIFIED"}
        </span>
        <h2>{signup ? "Create your workspace" : "Access your workspace"}</h2>
        <p>
          {signup
            ? "Start understanding your digital footprint."
            : "Continue managing your digital privacy."}
        </p>
        <form onSubmit={submit} noValidate>
          {signup && (
            <Field
              label="FULL NAME"
              name="name"
              type="text"
              placeholder="Your name"
              error={errors.name}
            />
          )}
          <Field
            label="EMAIL ADDRESS"
            name="email"
            type="email"
            placeholder="you@example.com"
            error={errors.email}
          />
          <Field
            label="PASSWORD"
            name="password"
            type={showPassword ? "text" : "password"}
            placeholder="At least 8 characters"
            error={errors.password}
            action={showPassword ? "Hide" : "Show"}
            onAction={() => setShowPassword(!showPassword)}
          />
          {signup && (
            <Field
              label="CONFIRM PASSWORD"
              name="confirm"
              type={showConfirm ? "text" : "password"}
              placeholder="Repeat your password"
              error={errors.confirm}
              action={showConfirm ? "Hide" : "Show"}
              onAction={() => setShowConfirm(!showConfirm)}
            />
          )}
          <div className="form-options">
            <label className="check">
              <input type="checkbox" name="terms" />
              <span />
              {signup
                ? "I agree to the Terms and Privacy Policy"
                : "Keep me signed in"}
            </label>
            {!signup && <button type="button">Forgot password?</button>}
          </div>
          {errors.terms && (
            <small className="form-error" role="alert">
              {errors.terms}
            </small>
          )}
          <Button type="submit">{signup ? "Create account" : "Log in"}</Button>
        </form>
        <div className="auth__switch">
          {signup ? "Already have an account?" : "New to Privora?"}
          <button onClick={() => navigate(signup ? "login" : "signup")}>
            {signup ? "Log in" : "Create account"}
          </button>
        </div>
        <button className="back-link" onClick={() => navigate("home")}>
          ← Back to home
        </button>
      </motion.div>
    </main>
  )
}

const Field = ({
  label,
  name,
  type,
  placeholder,
  error,
  action,
  onAction,
}: {
  label: string
  name: string
  type: string
  placeholder: string
  error?: string
  action?: string
  onAction?: () => void
}) => (
  <label className={`field ${error ? "field--error" : ""}`}>
    <span>{label}</span>
    <div>
      <input
        name={name}
        type={type}
        placeholder={placeholder}
        required
        aria-invalid={!!error}
        aria-describedby={error ? `${name}-error` : undefined}
      />
      {action && (
        <button type="button" onClick={onAction}>
          {action}
        </button>
      )}
    </div>
    {error && (
      <small id={`${name}-error`} role="alert">
        {error}
      </small>
    )}
  </label>
)

const onboardingSteps = [
  {
    eyebrow: "DISCOVERY SCOPE",
    title: "What accounts do you want to review?",
    copy: "Choose any online spaces you want to organise. Privora only works with the information and access you provide.",
    choices: [
      [
        "Internship and job portals",
        "Applications, recruiting profiles, and career sites",
      ],
      ["Online courses", "Learning platforms and course communities"],
      ["Hackathons", "Competitions, submissions, and team platforms"],
      ["Events and communities", "Event tools, groups, and member profiles"],
      ["Other online services", "Any other services you want to review"],
    ],
  },
  {
    eyebrow: "DATA CONCERNS",
    title: "What information concerns you?",
    copy: "Select the personal data categories you’re most concerned about.",
    choices: [
      ["Email addresses", "Personal, academic, and work addresses"],
      ["Phone numbers", "Current and previous contact numbers"],
      [
        "Resumes and career information",
        "CVs, applications, and employment details",
      ],
      ["Profile details", "Names, bios, photos, and public identity"],
      ["Uploaded documents", "Files submitted to online services"],
      ["Other personal information", "Anything else you want to track"],
    ],
  },
  {
    eyebrow: "PRIVACY GOALS",
    title: "How can Privora help?",
    copy: "Choose the tasks you want to prioritize in your workspace.",
    choices: [
      [
        "Discover forgotten accounts",
        "Organise possible accounts from available information",
      ],
      [
        "Understand privacy policies",
        "Translate relevant terms into clear language",
      ],
      [
        "Review shared information",
        "Examine personal data you supplied or may have shared",
      ],
      [
        "Explore removal options",
        "Understand deactivation and data-removal choices",
      ],
      [
        "Receive recommendations",
        "Get AI-assisted explanations and possible next steps",
      ],
    ],
  },
  {
    eyebrow: "REVIEW PREFERENCE",
    title: "How should recommendations work?",
    copy: "Consequential actions always require your approval. Choose how you prefer to review recommendations.",
    choices: [
      [
        "Review every recommendation individually",
        "Consider and decide on each recommendation one at a time",
      ],
      [
        "See recommendations first",
        "Review the full set, then choose what you want to do",
      ],
    ],
  },
]

const Onboarding = ({ navigate }: { navigate: (view: View) => void }) => {
  const [step, setStep] = useState(0)
  const [selected, setSelected] = useState<Record<number, string[]>>({})
  const data = onboardingSteps[step]
  const toggle = (choice: string) =>
    setSelected((all) => ({
      ...all,
      [step]: all[step]?.includes(choice)
        ? all[step].filter((x) => x !== choice)
        : [...(all[step] || []), choice],
    }))
  return (
    <main className="onboarding">
      <div className="onboarding__bar">
        <div className="brand">
          <Mark small />
          <span>PRIVORA</span>
        </div>
        <span>SETUP / 0{step + 1} OF 04</span>
        <button onClick={() => navigate("dashboard")}>Skip for now</button>
      </div>
      <div className="progress">
        <motion.i animate={{ width: `${((step + 1) / 4) * 100}%` }} />
      </div>
      <AnimatePresence mode="wait">
        <motion.section
          className="onboarding__content"
          key={step}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
        >
          <Label>{data.eyebrow}</Label>
          <h1>{data.title}</h1>
          <p>{data.copy}</p>
          <div className="choice-grid">
            {data.choices.map(([title, copy], i) => {
              const active = selected[step]?.includes(title)
              return (
                <button
                  className={active ? "choice choice--active" : "choice"}
                  onClick={() => toggle(title)}
                  key={title}
                >
                  <span className="choice__index">0{i + 1}</span>
                  <i className="choice__check">{active ? "✓" : "+"}</i>
                  <strong>{title}</strong>
                  <small>{copy}</small>
                </button>
              )
            })}
          </div>
          <div className="onboarding__actions">
            <button disabled={step === 0} onClick={() => setStep(step - 1)}>
              ← Back
            </button>
            <Button
              onClick={() =>
                step === 3 ? navigate("dashboard") : setStep(step + 1)
              }
            >
              {step === 3 ? "Open dashboard" : "Continue"}
            </Button>
          </div>
        </motion.section>
      </AnimatePresence>
    </main>
  )
}

const Dashboard = ({ navigate }: { navigate: (view: View) => void }) => {
  const [tab, setTab] = useState("Overview")

  const [dataMap, setDataMap] = useState<DataMapResponse | null>(null)
  const [dataMapLoading, setDataMapLoading] = useState(true)
  const [dataMapError, setDataMapError] = useState<string | null>(null)
  const [rules, setRules] = useState<RulesResponse | null>(null)
  const [rulesLoading, setRulesLoading] = useState(true)
  const [rulesError, setRulesError] = useState<string | null>(null)

  // ✅ PASTE THE NEW STATE HERE
  const [auditLogs, setAuditLogs] =
    useState<AuditLogsResponse | null>(null)
  const [auditLogsLoading, setAuditLogsLoading] = useState(true)
  const [auditLogsError, setAuditLogsError] =
    useState<string | null>(null)

  // Existing Personal Data useEffect starts here
  useEffect(() => {
    let cancelled = false

    // Keep your existing dataMap API code here...

    apiGet<DataMapResponse>("/data-map/1")
      .then((result) => {
        if (!cancelled) {
          setDataMap(result)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDataMapError(
            error instanceof Error
              ? error.message
              : "Unable to load personal data.",
          )
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDataMapLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

useEffect(() => {
  let cancelled = false

  apiGet<AuditLogsResponse>("/audit-logs/1")
    .then((result) => {
      if (!cancelled) {
        setAuditLogs(result)
      }
    })
    .catch((error: unknown) => {
      if (!cancelled) {
        setAuditLogsError(
          error instanceof Error
            ? error.message
            : "Unable to load activity history."
        )
      }
    })
    .finally(() => {
      if (!cancelled) {
        setAuditLogsLoading(false)
      }
    })

  return () => {
    cancelled = true
  }
}, [])

useEffect(() => {
  let cancelled = false

  apiGet<RulesResponse>("/rules/1")
    .then((result) => {
      if (!cancelled) {
        setRules(result)
      }
    })
    .catch((error: unknown) => {
      if (!cancelled) {
        setRulesError(
          error instanceof Error
            ? error.message
            : "Unable to load backend recommendations.",
        )
      }
    })
    .finally(() => {
      if (!cancelled) {
        setRulesLoading(false)
      }
    })

  return () => {
    cancelled = true
  }
}, [])

useEffect(() => {
  let cancelled = false

  const loadPrivacyActions = async () => {
    try {
      const response = await apiGet<PrivacyActionsResponse>(
        "/privacy-actions/1",
      )

      if (cancelled) return

      // The backend returns newest actions first.
      const latestByAccount = new Map<
        number,
        PrivacyActionsResponse["actions"][number]
      >()

      for (const action of response.actions) {
        if (!latestByAccount.has(action.account_id)) {
          latestByAccount.set(action.account_id, action)
        }
      }

      const currentRules = await apiGet<RulesResponse>("/rules/1")

if (cancelled) return

setRules(currentRules)

const mappedRecommendations: Recommendation[] =
  currentRules.recommendations.map((rule) => {
    const action = latestByAccount.get(rule.account_id)

    const statusMap: Record<string, string> = {
      PENDING: "Pending approval",
      APPROVED: "Approved — not executed",
      REJECTED: "Rejected",
    }

    return {
      id: rule.account_id,
      accountId: rule.account_id,
      actionId: action?.id ?? null,
      status: action
        ? statusMap[action.status] ?? "Proposed"
        : "Proposed",
      title:
        rule.recommendation === "REVIEW"
          ? `Review ${rule.service} account`
          : `Keep ${rule.service} account`,
      account: rule.service,
      why: rule.reason,
      next: rule.requires_user_approval
        ? "Review this recommendation and approve any privacy action before it is carried out."
        : "Review this recommendation and choose the next step.",
    }
  })

setRecommendations(mappedRecommendations)
    } catch (error) {
      if (!cancelled) {
        setActionError(
          error instanceof Error
            ? error.message
            : "Could not load existing privacy actions.",
        )
      }
    }
  }

  void loadPrivacyActions()

  return () => {
    cancelled = true
  }
}, [])

  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState("All")
  const [reviewing, setReviewing] = useState(false)
  const [recommendations, setRecommendations] =
  useState<Recommendation[]>([])

const [actionError, setActionError] = useState<string | null>(null)
const [actionMessage, setActionMessage] = useState<string | null>(null)
const [actionBusyId, setActionBusyId] = useState<number | null>(null)

  const accounts = [
    {
      icon: "J",
      name: "JobBoard",
      category: "Career",
      status: "Needs review",
      data: "Email, resume",
      reviewed: "Not yet reviewed",
    },
    {
      icon: "H",
      name: "Hackathon Portal",
      category: "Community",
      status: "Reviewed",
      data: "Email, profile",
      reviewed: "12 May 2025",
    },
    {
      icon: "D",
      name: "Dropbox",
      category: "Storage",
      status: "Needs review",
      data: "Email, documents",
      reviewed: "03 Apr 2025",
    },
    {
      icon: "C",
      name: "CourseHub",
      category: "Learning",
      status: "Reviewed",
      data: "Email, course activity",
      reviewed: "18 May 2025",
    },
  ]
  const filteredAccounts = accounts.filter(
    (account) =>
      (filter === "All" || account.status === filter) &&
      account.name.toLowerCase().includes(search.toLowerCase()),
  )

const setDecision = async (id: number, status: string) => {
  const item = recommendations.find((rec) => rec.id === id)

  if (!item || actionBusyId !== null) return

  // Prevent duplicate decisions on completed recommendations.
  if (
    item.status === "Approved — not executed" ||
    item.status === "Rejected"
  ) {
    setActionError(null)
    setActionMessage("This recommendation already has a final decision.")
    return
  }

  setActionError(null)
  setActionMessage(null)
  setActionBusyId(id)

  try {
    let actionId = item.actionId

    // Create a pending action if this recommendation has none.
    if (actionId === null) {
      const created = await apiPost<CreateActionResponse>(
        "/privacy-actions/1",
        {
          account_id: item.accountId,
          action_type: "REVIEW_ACCOUNT",
          description: item.title,
        },
      )

      actionId = created.id

      setRecommendations((items) =>
        items.map((rec) =>
          rec.id === id
            ? { ...rec, actionId, status: "Pending approval" }
            : rec,
        ),
      )

      setActionMessage(
        `Action #${actionId} created and awaiting your decision.`,
      )

      // Decide only after the pending action has been created.
      return
    }

    // Reviewing keeps the action pending.
    if (status === "Under review") {
      setActionMessage(
        `Action #${actionId} is awaiting your decision.`,
      )
      return
    }

    const decision =
      status === "Rejected" ? "REJECT" : "APPROVE"

    await apiPost<unknown>(
      `/privacy-actions/1/${actionId}/review`,
      { decision },
    )

    const finalStatus =
      decision === "REJECT"
        ? "Rejected"
        : "Approved — not executed"

    setRecommendations((items) =>
      items.map((rec) =>
        rec.id === id
          ? { ...rec, actionId, status: finalStatus }
          : rec,
      ),
    )

    setActionMessage(
      `Action #${actionId} recorded as ${decision}. No external account changes were made.`,
    )
  } catch (error) {
    setActionError(
      error instanceof Error
        ? error.message
        : "Something went wrong.",
    )
  } finally {
    setActionBusyId(null)
  }
}

  const nav = [
    "Overview",
    "My Accounts",
    "Personal Data",
    "AI Recommendations",
    "Activity History",
    "Settings",
  ]

  return (
    <main className="dashboard">
      <aside className="sidebar">
        <div className="sidebar__top">
          <span>DEMO WORKSPACE</span>
          <strong>{tab}</strong>
        </div>
        <nav>
          {nav.map((item, i) => (
            <button
              className={tab === item ? "active" : ""}
              onClick={() => setTab(item)}
              key={item}
            >
              <span>{["⌂", "◎", "◫", "↗", "≡", "⚙"][i]}</span>
              {item}
            </button>
          ))}
        </nav>
        <div className="sidebar__notice">
          <span>DEMO DATA</span>
          <p>No live accounts or external services are connected.</p>
        </div>
        <button className="sidebar__settings" onClick={() => navigate("home")}>
          <span>↪</span> Log out
        </button>
      </aside>
      <div className="dash-content">
        <div className="mobile-tabs" aria-label="Dashboard sections">
          {nav.map((item) => (
            <button
              className={tab === item ? "active" : ""}
              onClick={() => setTab(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="dash-heading">
          <div>
            <Label>PRIVORA / DEMONSTRATION</Label>
            <h1>
              {tab === "Overview" ? (
                <>
                  Your digital life,
                  <br />
                  organised.
                </>
              ) : (
                tab
              )}
            </h1>
          </div>
          {tab === "My Accounts" && (
            <button
              className="scan-button"
              onClick={() => setReviewing(!reviewing)}
            >
              <span>{reviewing ? "×" : "+"}</span>{" "}
              {reviewing ? "Cancel review" : "Prepare review"}
            </button>
          )}
        </div>

        {tab === "Overview" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="demo-banner">
              <strong>DEMO WORKSPACE</strong>
              <span>
                Sample information for product demonstration only. No real
                discovery or external action has occurred.
              </span>
            </div>
            <div className="metrics">
              {[
                ["04", "ACCOUNTS ADDED", "DEMO RECORDS"],
                ["02", "NEEDING REVIEW", "ATTENTION NEEDED"],
                ["03", "PENDING RECOMMENDATIONS", "AWAITING DECISION"],
                ["01", "ACTIONS COMPLETED", "CONFIRMED DEMO STATUS"],
              ].map(([value, label, note]) => (
                <div className="metric" key={label}>
                  <span>{label}</span>
                  <strong>{value}</strong>
                  <small>{note}</small>
                </div>
              ))}
            </div>
            <div className="dash-grid">
              <section className="accounts-panel">
                <div className="panel-heading">
                  <div>
                    <Label>ACCOUNTS</Label>
                    <h2>Recently reviewed</h2>
                  </div>
                  <button onClick={() => setTab("My Accounts")}>
                    View all <Arrow />
                  </button>
                </div>
                <div className="account-list">
                  {accounts.slice(0, 3).map((account) => (
                    <AccountRow account={account} key={account.name} />
                  ))}
                </div>
              </section>
              <section className="data-map">
                <div className="panel-heading">
                  <div>
                    <Label>INFORMATION MAP</Label>
                    <h2>Known and potential data</h2>
                  </div>
                </div>
                <div className="data-orbit">
                  <div className="data-orbit__center">YOU</div>
                  {[
                    "SUPPLIED",
                    "POTENTIAL",
                    "CONTACT",
                    "CAREER",
                    "DOCUMENTS",
                  ].map((x, i) => (
                    <span className={`node node--${i + 1}`} key={x}>
                      {x}
                    </span>
                  ))}
                </div>
              </section>
              <RecommendationPanel
                items={recommendations}
                setDecision={setDecision}
                actionError={actionError}
                actionMessage={actionMessage}
              />
            </div>
          </motion.div>
        )}

        {tab === "My Accounts" && (
          <motion.section
            className="wide-panel"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <AnimatePresence>
              {reviewing && (
                <motion.div
                  className="review-loader"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                >
                  <span className="ai-orb">
                    <i />
                    <i />
                  </span>
                  <div>
                    <strong>Preparing your review.</strong>
                    <p>
                      Organising the demo account details already shown below.
                      No external account scan is running.
                    </p>
                  </div>
                  <div className="review-loader__line">
                    <i />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div className="demo-banner">
              <strong>DEMO DATA</strong>
              <span>
                These sample accounts have not been discovered from external
                services.
              </span>
            </div>
            <div className="account-tools">
              <label>
                <span className="sr-only">Search accounts</span>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search accounts…"
                />
              </label>
              <div className="filters">
                {["All", "Needs review", "Reviewed"].map((x) => (
                  <button
                    className={filter === x ? "active" : ""}
                    onClick={() => setFilter(x)}
                    key={x}
                  >
                    {x}
                  </button>
                ))}
              </div>
            </div>
            <div className="account-table account-table--head">
              <span>ACCOUNT</span>
              <span>CATEGORY</span>
              <span>KNOWN OR POTENTIAL DATA</span>
              <span>LAST REVIEWED</span>
              <span>STATUS</span>
              <span />
            </div>
            {filteredAccounts.map((account) => (
              <AccountRow account={account} detailed key={account.name} />
            ))}
          </motion.section>
        )}

               {tab === "Personal Data" && (
          <motion.div
            className="data-cards"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="demo-banner">
              <strong>DATABASE DATA</strong>
              <span>
                These records come from Privora's database. Example
                descriptions are not proof that external services were checked.
              </span>
            </div>

            {dataMapLoading && (
              <p role="status">Loading personal data records…</p>
            )}

            {dataMapError && (
              <p role="alert">
                Unable to load personal data: {dataMapError}
              </p>
            )}

            {!dataMapLoading &&
              !dataMapError &&
              dataMap?.accounts.length === 0 && (
                <p>No account records were found for this user.</p>
              )}

            {dataMap?.accounts.map((account, index) => (
              <section className="data-card" key={account.account_id}>
                <span>{String(index + 1).padStart(2, "0")}</span>

                <h2>{account.service}</h2>

                <div>
                  <p>
                    Account status
                    <em>{account.status}</em>
                  </p>

                  <p>
                    Website
                    <em>
                      {account.website ? (
                        <a
                          href={account.website}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {account.website}
                        </a>
                      ) : (
                        "Not available"
                      )}
                    </em>
                  </p>

                  <p>
                    Last activity
                    <em>
                      {account.last_activity
                        ? new Date(account.last_activity).toLocaleString()
                        : "Not recorded"}
                    </em>
                  </p>

                  <p>
                    Recorded data categories
                    <em>{account.data_record_count}</em>
                  </p>

                  {account.data_records.length > 0 ? (
                    account.data_records.map((record, recordIndex) => (
                      <p key={`${account.account_id}-${recordIndex}`}>
                        {record.category}
                        <em>
                          {record.description ??
                            "No description recorded"}
                        </em>
                      </p>
                    ))
                  ) : (
                    <p>
                      No data categories recorded
                      <em>Database record</em>
                    </p>
                  )}
                </div>
              </section>
            ))}
          </motion.div>
        )}

        {tab === "AI Recommendations" && (
  <RecommendationPanel
    items={recommendations}
    setDecision={setDecision}
    actionError={actionError}
    actionMessage={actionMessage}
    standalone
  />
)}

        {tab === "Activity History" && (
          <motion.section
            className="history wide-panel"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="demo-banner">
              <strong>AUDIT LOG</strong>
<span>Recorded privacy-action events.</span>
            </div>

{auditLogsLoading && (
  <p role="status">Loading activity history…</p>
)}

{auditLogsError && (
  <p role="alert">
    Unable to load activity history: {auditLogsError}
  </p>
)}

{!auditLogsLoading &&
  !auditLogsError &&
  auditLogs?.logs.length === 0 && (
    <p>No audit events recorded yet.</p>
  )}

{auditLogs?.logs.map((log) => (
  <div className="history-row" key={log.id}>
    <span>{new Date(log.created_at).toLocaleString()}</span>
    <i>{log.event_type.split("_").join(" ")}</i>
    <strong>{log.details}</strong>
    <em>
      {log.privacy_action_id
        ? `Action #${log.privacy_action_id}`
        : "General event"}
    </em>
  </div>
))}

          </motion.section>
        )}

        {tab === "Settings" && (
          <motion.section
            className="settings-panel wide-panel"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <Label>PROFILE & PREFERENCES</Label>
            <h2>Workspace settings</h2>
            <div className="settings-grid">
              <Field
                label="FULL NAME"
                name="settings-name"
                type="text"
                placeholder="Sam K."
              />
              <Field
                label="EMAIL ADDRESS"
                name="settings-email"
                type="email"
                placeholder="sam@example.com"
              />
            </div>
            <label className="setting-toggle">
              <span>
                <strong>Recommendation summaries</strong>
                <small>
                  Receive a digest when new demo recommendations are ready.
                </small>
              </span>
              <input type="checkbox" defaultChecked />
            </label>
            <label className="setting-toggle">
              <span>
                <strong>Reduced data display</strong>
                <small>Hide potentially inferred information by default.</small>
              </span>
              <input type="checkbox" />
            </label>
            <Button>Save preferences</Button>
            <button className="logout-button" onClick={() => navigate("home")}>
              Log out of demo workspace
            </button>
          </motion.section>
        )}
      </div>
    </main>
  )
}

type Account = {
  icon: string
  name: string
  category: string
  status: string
  data: string
  reviewed: string
}

const AccountRow = ({
  account,
  detailed = false,
}: {
  account: Account
  detailed?: boolean
}) =>
  detailed ? (
    <div className="account-table">
      <div className="account-name">
        <i>{account.icon}</i>
        <strong>{account.name}</strong>
      </div>
      <span>{account.category}</span>
      <span>{account.data}</span>
      <span>{account.reviewed}</span>
      <em className={account.status === "Needs review" ? "review" : ""}>
        {account.status}
      </em>
      <button>View details</button>
    </div>
  ) : (
    <div className="account">
      <i>{account.icon}</i>
      <div>
        <strong>{account.name}</strong>
        <span>
          {account.category} · {account.data}
        </span>
      </div>
      <em className={account.status === "Needs review" ? "review" : ""}>
        {account.status}
      </em>
      <button aria-label={`View ${account.name} details`}>
        <Arrow />
      </button>
    </div>
  )



const RecommendationPanel = ({
  items,
  setDecision,
  standalone = false,
  actionError,
  actionMessage,
}: {
  items: Recommendation[]
  setDecision: (id: number, status: string) => Promise<void>
  standalone?: boolean
  actionError?: string | null
  actionMessage?: string | null
}) => (

  <motion.section
    className={`recommendations ${
      standalone ? "recommendations--standalone" : ""
    }`}
    initial={standalone ? { opacity: 0 } : undefined}
    animate={standalone ? { opacity: 1 } : undefined}
  >
    <div className="panel-heading">
      <div>
        <Label>AI-ASSISTED / DEMO</Label>
        <h2>Recommendations to review</h2>
      </div>
      <span className="demo-tag">NOT EXECUTED</span>
    </div>
    {actionError && <p role="alert">{actionError}</p>}
    {actionMessage && <p role="status">{actionMessage}</p>}
    {items.map((item) => (
      <motion.div className="recommendation" key={item.id} layout>
        <span className="risk">AI</span>
        <div className="recommendation__body">
          <strong>{item.title}</strong>
          <small>{item.account}</small>
          <p>
            <b>Why it may matter:</b> {item.why}
          </p>
          <p>
            <b>Possible next step:</b> {item.next}
          </p>
          <em>{item.status}</em>
        </div>
        <div className="recommendation__actions">
          <button onClick={() => setDecision(item.id, "Rejected")}>
            Reject
          </button>
          <button onClick={() => setDecision(item.id, "Under review")}>
            Review
          </button>
          <button
            onClick={() => setDecision(item.id, "Approved — not executed")}
          >
            Approve <Arrow />
          </button>
        </div>
      </motion.div>
    ))}
  </motion.section>
)

const Chat = () => {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([
    {
      role: "system",
      text: "AI service not connected. You can compose a question, but no model response will be fabricated in this demo.",
    },
  ])
  const send = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    const text = input
    setMessages((m) => [
      ...m,
      { role: "user", text },
      {
        role: "system",
        text: "Message not sent: a real AI backend has not been configured.",
      },
    ])
    setInput("")
  }
  return (
    <div className="chat-wrap">
      <AnimatePresence>
        {open && (
          <motion.div
            className="chat"
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
          >
            <div className="chat__head">
              <div>
                <span className="ai-orb ai-orb--small">
                  <i />
                  <i />
                </span>
                <span>
                  <strong>PRIVORA AI</strong>
                  <small>OFFLINE / DEMO MODE</small>
                </span>
              </div>
              <button onClick={() => setOpen(false)}>×</button>
            </div>
            <div className="chat__messages">
              {messages.map((m, i) => (
                <div className={`message message--${m.role}`} key={i}>
                  {m.text}
                </div>
              ))}
            </div>
            <div className="chat__prompts">
              {[
                "What personal data might I have shared?",
                "Help me review a forgotten account.",
                "Explain this privacy recommendation.",
                "What options do I have for removing my data?",
              ].map((x) => (
                <button onClick={() => setInput(x)} key={x}>
                  {x}
                </button>
              ))}
            </div>
            <form onSubmit={send}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Privora…"
                aria-label="Ask Privora"
              />
              <button aria-label="Send">
                <Arrow />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        className="chat-trigger"
        onClick={() => setOpen(!open)}
        aria-label="Open Privora assistant"
      >
        <span className="chat-trigger__pulse" />
        <span className="ai-orb">
          <i />
          <i />
        </span>
      </button>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<View>("home")
  const navigate = (next: View) => {
    setView(next)
    window.scrollTo({ top: 0, behavior: "smooth" })
  }
  useEffect(() => {
    document.title =
      view === "home"
        ? "Privora — Your Digital Life. Your Control."
        : `Privora — ${view[0].toUpperCase()}${view.slice(1)}`
  }, [view])
  return (
    <div className="app">
      {view !== "onboarding" && <Header view={view} navigate={navigate} />}
      <AnimatePresence mode="wait">
        <motion.div
          key={view}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.28 }}
        >
          {view === "home" && <Landing navigate={navigate} />}
          {(view === "login" || view === "signup") && (
            <Auth mode={view} navigate={navigate} />
          )}
          {view === "onboarding" && <Onboarding navigate={navigate} />}
          {view === "dashboard" && <Dashboard navigate={navigate} />}
        </motion.div>
      </AnimatePresence>
      <Chat />
    </div>
  )
}
