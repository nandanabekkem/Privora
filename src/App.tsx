import { FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
} from "firebase/auth"
import { apiGet, apiPost } from "./api"
import { firebaseAuth } from "./firebase"
import LegalPage, { type LegalPageKind } from "./LegalPages"

type View = "home" | "login" | "signup" | "onboarding" | "dashboard" | "privacy" | "terms" | "not-found"

const routeForView: Record<Exclude<View, "not-found">, string> = {
  home: "/",
  login: "/login",
  signup: "/signup",
  onboarding: "/onboarding",
  dashboard: "/dashboard",
  privacy: "/privacy",
  terms: "/terms",
}

const viewForPath = (pathname: string): View => {
  const normalized = pathname.replace(/\/+$/, "") || "/"
  const route = Object.entries(routeForView).find(([, path]) => path === normalized)
  return route?.[0] as View | undefined ?? "not-found"
}

type UserProfile = {
  id: number | string
  uid: string
  name: string
  email: string
}


type DiscoveryResponse = {
  status: string
  source: "synthetic" | "gmail"
  count: number
  accounts: DiscoveredAccount[]
  source_label?: string
}

type DiscoveredAccount = {
  service_name: string
  domain: string
  relationship: string | null
  source: string
  first_seen: string | null
  last_activity: string | null
  data_categories: string[]
  account_status: "active" | "dormant" | "unknown"
}

type DataMapResponse = {
  user_id: number | string
  account_count: number
  accounts: {
    account_id: number | string
    service: string
    domain: string | null
    website: string | null
    purpose: string | null
    purpose_source_url: string | null
    status: string
    last_activity: string | null
    last_evidence_at: string | null
    discovery_source: string | null
    evidence_confidence: "low" | "unknown"
    evidence_note: string
    data_records: {
      category: string
      description: string | null
    }[]
    data_record_count: number
  }[]
}

type DormancyResponse = {
  accounts: {
    account_id: number | string
    is_dormant: boolean | null
    last_activity: string | null
    reason: string
    needs_review: boolean
  }[]
}

type AuditLogsResponse = {
  user_id: number | string
  count: number
  logs: {
    id: number | string
    privacy_action_id: number | string | null
    event_type: string
    details: string
    created_at: string
  }[]
}


type PrivacyActionsResponse = {
  user_id: number | string
  count: number
  actions: {
    id: number | string
    account_id: number | string
    action_type: string
    description: string
    status: string
    requires_approval: boolean
    created_at: string
    reviewed_at: string | null
    request_status?: string | null
    reply_status?: string | null
    reply_detection_source?: string | null
    reply_candidate_at?: string | null
    request_subject?: string | null
    request_body?: string | null
    channel_url?: string | null
    channel_catalogued?: boolean
    channel_type?: string | null
    channel_source_url?: string | null
    channel_email?: string | null
  }[]
}


type RulesResponse = {
  user_id: number | string
  days_threshold: number
  saved_policy_count: number
  account_count: number
  recommendation_count: number
  recommendations: {
    account_id: number | string
    service: string
    recommendation: "KEEP" | "REVIEW"
    reason: string
    days_threshold: number
    applied_policy_count: number
    requires_user_approval: boolean
    data_context?: string
    evidence_note?: string | null
    analysis_mode?: string
    fallback_reason?: string | null
    ai_explanation?: string | null
  }[]
  note: string
}

type Recommendation = {
  id: number | string
  accountId: number | string
  actionId: number | string | null
  status: string
  title: string
  account: string
  decision: "KEEP" | "REVIEW"
  why: string
  dataContext: string
  evidenceNote?: string | null
}


type CreateActionResponse = {
  id: number | string
  user_id: number | string
  account_id: number | string
  action_type: string
  description: string
  status: string
  requires_approval: boolean
  created_at: string
  message: string
}

type AccountAnalysisResponse = {
  account_id: string
  service: string
  website: string | null
  catalog_purpose: string | null
  purpose_source_url: string | null
  discovery_source: string
  evidence_confidence: string
  last_evidence_at: string | null
  evidence_note: string
  sensitivity: {
    categories: string[]
    sensitive_categories: string[]
    sensitivity: string
    limitations: string
  }
  analysis_mode: string
  explanation: string
  fallback_reason?: string
  limitations: string
}

type DeletionDraft = {
  id: number | string
  account_id: number | string
  status: string
  request_status: string
  subject: string
  body: string
  channel_url: string | null
  channel_catalogued: boolean
  channel_type?: string | null
  channel_source_url?: string | null
  channel_email?: string | null
  channel_notice?: string
  reply_status?: string
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
    <span className="guardian__tag guardian__tag--bottom">USER CONTROL</span>
    <div className="guardian__scan" />
  </div>
)

const Header = ({
  view,
  navigate,
  user,
}: {
  view: View
  navigate: (view: View) => void
  user: UserProfile | null
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
          <button
            className="avatar"
            onClick={() => navigate("dashboard")}
            aria-label={user ? `Signed in as ${user.name}` : "Current demo user"}
            title={user?.email ?? "Demo session"}
          >
            {(user?.name || user?.email || "U")
              .trim()
              .split(/[\s@._-]+/)
              .filter(Boolean)
              .slice(0, 2)
              .map((part) => part[0]?.toUpperCase())
              .join("")}
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
      text: "Add accounts yourself or optionally scan a bounded set of Gmail message headers—sender, subject, and date, not message bodies—to identify service candidates. Results can be incomplete and do not prove ownership or activity.",
      stat: "ACCOUNT CANDIDATES",
    },
    {
      no: "02",
      type: "classify" as const,
      title: "Understand what you shared.",
      text: "Review the categories and notes recorded in your inventory. Gmail-derived categories are marked as inferred and may not describe information a provider currently holds.",
      stat: "RECORDED AND INFERRED",
    },
    {
      no: "03",
      type: "recommend" as const,
      title: "Understand your recorded information.",
      text: "Privacy Analysis and account chat currently use local rules and the account context stored in Privora. They do not inspect a provider's systems or call an external AI service.",
      stat: "LOCAL ANALYSIS",
    },
    {
      no: "04",
      type: "act" as const,
      title: "Recommendations, not blind automation.",
      text: "Local rules use recorded activity, categories, and saved policies to suggest KEEP or REVIEW. A recommendation does not itself change or delete an external account.",
      stat: "LOCAL RECOMMENDATIONS",
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
            <Label>PERSONAL DATA, ON YOUR TERMS</Label>
            <span>ACCOUNT / PRIVACY</span>
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
              Privora is a personal data lifecycle and digital-footprint
              management assistant. Organize candidate services, review stored
              information, and decide what to do next.
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
              From candidate discovery to an informed decision. External
              requests require your approval and explicit action.
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
                "Review account-specific local analysis and recorded-data recommendations.",
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
                "Privora is a personal data lifecycle assistant for organizing account candidates and reviewing information recorded in your inventory.",
              ],
              [
                "What does Gmail discovery access?",
                "With your authorization, Privora reads a bounded set of Gmail message metadata such as sender, subject, and date. It does not read message bodies. Candidate results can be incomplete and do not prove account ownership, service activity, or current provider data holdings.",
              ],
              [
                "How does it help review forgotten accounts?",
                "Privora organizes details you add and can use optional Gmail metadata to identify service candidates. It does not search the entire internet or verify that you own a candidate account.",
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
                "Local rules compare recorded activity, categories, and saved policies to recommend KEEP or REVIEW. You decide what to do next.",
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
      <section className="deletion-disclaimer" aria-labelledby="deletion-disclaimer-title">
        <div className="deletion-disclaimer__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z" />
            <path d="M12 8v4m0 3h.01" />
          </svg>
        </div>
        <div>
          <h2 id="deletion-disclaimer-title">A note on data deletion</h2>
          <p>Requesting or completing account deletion does not necessarily mean all personal data associated with that account has been erased. Services may retain certain information for legal, security, backup, or other disclosed purposes. Privora helps you manage and track your requests, but deletion and erasure of retained data must be confirmed by the service provider.</p>
        </div>
      </section>
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
      Personal data lifecycle and digital-footprint management.
      <br />
      Your digital life. Your decisions.
    </p>
    <div>
      <button onClick={() => navigate("login")}>Log in</button>
      <button onClick={() => navigate("signup")}>Create account</button>
      <a href="/privacy" onClick={(event) => { event.preventDefault(); navigate("privacy") }}>Privacy Policy</a>
      <a href="/terms" onClick={(event) => { event.preventDefault(); navigate("terms") }}>Terms of Service</a>
    </div>
    <span>© {new Date().getFullYear()} PRIVORA</span>
  </footer>
)

const Auth = ({
  mode,
  navigate,
  onAuthenticated,
}: {
  mode: "login" | "signup"
  navigate: (view: View) => void
  onAuthenticated: (profile: UserProfile) => void
}) => {
  const signup = mode === "signup"
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [authError, setAuthError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const submit = async (e: FormEvent) => {
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
    if (!firebaseAuth) {
      setAuthError(
        "Firebase Authentication is not configured. Set the VITE_FIREBASE_* web app values and reload.",
      )
      return
    }

    setAuthError(null)
    setSubmitting(true)
    try {
      const credential = signup
        ? await createUserWithEmailAndPassword(
            firebaseAuth,
            email.trim(),
            password,
          )
        : await signInWithEmailAndPassword(
            firebaseAuth,
            email.trim(),
            password,
          )

      if (signup) {
        await updateProfile(credential.user, { displayName: name.trim() })
      }

      const profile = await apiGet<UserProfile>("/auth/me")
      onAuthenticated(profile)
      navigate(signup ? "onboarding" : "dashboard")
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : "Authentication could not be completed.",
      )
    } finally {
      setSubmitting(false)
    }
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
          {signup ? "NEW IDENTITY / 01" : "FIREBASE AUTHENTICATION"}
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
          {authError && (
            <small className="form-error" role="alert">
              {authError}
            </small>
          )}
          <Button type="submit">
            {submitting
              ? "Connecting..."
              : signup
                ? "Create account"
                : "Log in"}
          </Button>
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
        "Get account-specific mock/local explanations and possible next steps",
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

const Dashboard = ({
  navigate,
  user,
  onLogout,
}: {
  navigate: (view: View) => void
  user: UserProfile | null
  onLogout: () => void
}) => {
  const userId = encodeURIComponent(String(user?.id ?? ""))
  const [tab, setTab] = useState(() => {
    const requestedTab = new URLSearchParams(window.location.search).get("tab")
    return ["Overview", "My Accounts", "Personal Data", "AI Recommendations", "Activity History", "Settings"].includes(requestedTab ?? "")
      ? requestedTab!
      : "Overview"
  })
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get("account"),
  )
  const [selectedAccountOwnerId, setSelectedAccountOwnerId] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get("accountOwner"),
  )

  const changeTab = (nextTab: string) => {
    const query = new URLSearchParams(window.location.search)
    query.set("tab", nextTab)
    const queryString = query.toString()
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${queryString ? `?${queryString}` : ""}${window.location.hash}`,
    )
    setTab(nextTab)
  }

  const openAccountDetails = (accountId: string | number) => {
    const selectedId = String(accountId)
    const query = new URLSearchParams(window.location.search)
    query.set("account", selectedId)
    query.set("accountOwner", String(user?.id ?? ""))
    const queryString = query.toString()
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${queryString ? `?${queryString}` : ""}${window.location.hash}`,
    )
    setSelectedAccountId(selectedId)
    setSelectedAccountOwnerId(String(user?.id ?? ""))
    changeTab("Personal Data")
  }

  const [dataMap, setDataMap] = useState<DataMapResponse | null>(null)
  const [dataMapLoading, setDataMapLoading] = useState(true)
  const [dataMapError, setDataMapError] = useState<string | null>(null)
  const [dormancyByAccount, setDormancyByAccount] = useState<Record<string, boolean | null>>({})
  const [dormancyLoading, setDormancyLoading] = useState(true)
  const [dormancyError, setDormancyError] = useState<string | null>(null)
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

    apiGet<DataMapResponse>(`/data-map/${userId}`)
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
  }, [userId])

  useEffect(() => {
    let cancelled = false
    apiGet<DormancyResponse>(`/dormant/${userId}`)
      .then((result) => {
        if (!cancelled) {
          setDormancyByAccount(Object.fromEntries(
            result.accounts.map((account) => [String(account.account_id), account.is_dormant]),
          ))
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) setDormancyError(error instanceof Error ? error.message : "Dormancy review could not be loaded.")
      })
      .finally(() => { if (!cancelled) setDormancyLoading(false) })
    return () => { cancelled = true }
  }, [userId])

useEffect(() => {
  let cancelled = false

  apiGet<AuditLogsResponse>(`/audit-logs/${userId}`)
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
}, [userId])

useEffect(() => {
  let cancelled = false

  const loadPrivacyActions = async () => {
    try {
      // A bounded metadata-only check links to messages Privora actually sent.
      // Failure to check replies must not prevent the dashboard from loading.
      try {
        const replyCheck = await apiPost<{ checked: number; reply_candidates: number; message: string }>(
          `/privacy-actions/${userId}/check-replies`,
          {},
        )
        if (replyCheck.reply_candidates > 0 && !cancelled) {
          setActionMessage(`${replyCheck.reply_candidates} possible Gmail reply found. Review it in Gmail and confirm it in the request card.`)
        }
      } catch {
        // The action list below remains available if Gmail cannot be checked.
      }
      const response = await apiGet<PrivacyActionsResponse>(
        `/privacy-actions/${userId}`,
      )

      if (cancelled) return

      setDeletionDrafts(Object.fromEntries(
        response.actions
          .filter((action) => action.action_type === "DELETE_REQUEST_DRAFT")
          .reverse()
          .map((action) => [String(action.account_id), {
            id: action.id,
            account_id: action.account_id,
            status: action.status,
            request_status: action.request_status ?? "PENDING_APPROVAL",
            subject: action.request_subject ?? "Deletion request",
            body: action.request_body ?? "",
            channel_url: action.channel_url ?? null,
            channel_catalogued: action.channel_catalogued ?? false,
            channel_type: action.channel_type ?? null,
            channel_source_url: action.channel_source_url ?? null,
            channel_email: action.channel_email ?? null,
            reply_status: action.reply_status ?? "NO_REPLY",
          } satisfies DeletionDraft]),
      ))

      // The backend returns newest actions first.
      const latestByAccount = new Map<
        number | string,
        PrivacyActionsResponse["actions"][number]
      >()

      for (const action of response.actions) {
        if (!latestByAccount.has(action.account_id)) {
          latestByAccount.set(action.account_id, action)
        }
      }

      const currentRules = await apiGet<RulesResponse>(`/rules/${userId}`)

if (cancelled) return

setRules(currentRules)
setRulesLoading(false)
setRulesError(null)

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
      decision: rule.recommendation,
      why: rule.reason,
      dataContext: rule.data_context ?? "Recorded: not available; inferred: not available.",
      evidenceNote: rule.evidence_note,
    }
  })

setRecommendations(mappedRecommendations)
    } catch (error) {
      if (!cancelled) {
        setRulesError(
          error instanceof Error
            ? error.message
            : "Unable to load backend recommendations.",
        )
        setRulesLoading(false)
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
}, [userId])


const [discoveredAccounts, setDiscoveredAccounts] =
  useState<DiscoveredAccount[]>([])
const [discoverySource, setDiscoverySource] =
  useState<DiscoveryResponse["source"]>("synthetic")
const [discoveryLoading, setDiscoveryLoading] = useState(false)
const [discoveryError, setDiscoveryError] = useState<string | null>(null)
const [discoveryRan, setDiscoveryRan] = useState(false)
const [gmailStatus, setGmailStatus] = useState<string>("checking")

useEffect(() => {
  let cancelled = false
  apiGet<{ status: string; connected: boolean }>("/discovery/gmail/status")
    .then((result) => { if (!cancelled) setGmailStatus(result.status) })
    .catch(() => { if (!cancelled) setGmailStatus("unavailable") })
  return () => { cancelled = true }
}, [userId])

const loadDiscoveredAccounts = async (
  source: DiscoveryResponse["source"] = "synthetic",
) => {
  setDiscoveryLoading(true)
  setDiscoveryError(null)

  try {
    const response = await apiPost<DiscoveryResponse>(
      `/discovery/run?source=${source}`,
      {},
    )

    setDiscoveredAccounts(response.accounts)
    setDiscoverySource(response.source)
    setDiscoveryRan(true)
    if (response.source === "gmail") {
      const inventory = await apiGet<DataMapResponse>(`/data-map/${userId}`)
      setDataMap(inventory)
    }
  } catch (error) {
    setDiscoveryError(
      error instanceof Error
        ? error.message
        : "Could not discover accounts.",
    )
  } finally {
    setDiscoveryLoading(false)
  }
}

const connectGmail = async () => {
  setDiscoveryError(null)
  try {
    const response = await apiPost<{ authorization_url: string }>(
      "/discovery/gmail/authorize",
      {},
    )
    window.location.assign(response.authorization_url)
  } catch (error) {
    setDiscoveryError(
      error instanceof Error ? error.message : "Could not connect Gmail.",
    )
  }
}

useEffect(() => {
  const result = new URLSearchParams(window.location.search).get("gmail")
  if (!result) return
  const reason = new URLSearchParams(window.location.search).get("reason")
  if (result === "connected") {
    setActionMessage("Gmail authorization was saved. Run Discover Gmail to verify access and scan message headers.")
    setGmailStatus("authorization_ready")
  } else if (result === "denied") {
    setDiscoveryError("Google consent was cancelled. No Gmail connection was saved.")
  } else if (reason === "configuration") {
    setDiscoveryError("Gmail connection could not be completed because backend OAuth or token-encryption settings are incomplete.")
  } else if (reason === "expired") {
    setDiscoveryError("The Google authorization attempt expired. Choose Connect Gmail and try again.")
  } else if (reason === "offline_access") {
    setDiscoveryError("Google did not return offline access. Revoke Privora in your Google Account, then connect again.")
  } else {
    setDiscoveryError("Google authorization could not be completed. Check the OAuth client and registered callback URI, then try again.")
  }
  window.history.replaceState({}, "", window.location.pathname)
}, [])


  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState("All")
  const [reviewing, setReviewing] = useState(false)
  const [recommendations, setRecommendations] =
  useState<Recommendation[]>([])

const [actionError, setActionError] = useState<string | null>(null)
const [actionMessage, setActionMessage] = useState<string | null>(null)
const [actionBusyId, setActionBusyId] = useState<number | string | null>(null)
const [deletionDrafts, setDeletionDrafts] = useState<Record<string, DeletionDraft>>({})
const [draftBusyId, setDraftBusyId] = useState<string | null>(null)
const [replyNotes, setReplyNotes] = useState<Record<string, string>>({})
const [analysisByAccount, setAnalysisByAccount] = useState<Record<string, AccountAnalysisResponse>>({})
const [analysisBusyId, setAnalysisBusyId] = useState<string | null>(null)

const storedAccounts: Account[] = (dataMap?.accounts ?? []).map((account) => ({
  id: account.account_id,
  icon: account.service.charAt(0).toUpperCase() || "?",
  name: account.service,
  category: account.data_records.map((record) => record.category).join(", ") || "Unclassified",
  status: dormancyByAccount[String(account.account_id)] === true
    ? "Dormant"
    : dormancyByAccount[String(account.account_id)] === false
      ? "Active"
      : dormancyByAccount[String(account.account_id)] === null
        ? "Status unknown"
        : account.status === "ACTIVE" ? "Active" : account.status === "DORMANT" ? "Dormant" : "Status unknown",
  data: account.website || account.domain || "Website not catalogued",
  purpose: account.purpose,
  sourceLabel: account.discovery_source === "gmail"
    ? `Gmail header candidate · ${account.evidence_confidence} confidence`
    : "Stored inventory record",
  lastEvidence: account.last_evidence_at
    ? new Date(account.last_evidence_at).toLocaleDateString()
    : account.last_activity
      ? new Date(account.last_activity).toLocaleDateString()
      : "Not recorded",
}))
const sampleAccounts: Account[] = discoveredAccounts.map((account) => ({
  id: account.domain,
  icon: account.service_name.charAt(0).toUpperCase() || "?",
  name: account.service_name,
  category: account.data_categories.length ? account.data_categories.join(", ") : "Unclassified",
  status: account.account_status === "active" ? "Active" : account.account_status === "dormant" ? "Dormant" : "Status unknown",
  data: account.domain,
  purpose: null,
  sourceLabel: "Synthetic sample — not real discovery",
  lastEvidence: account.last_activity ? new Date(account.last_activity).toLocaleDateString() : "Not recorded",
}))
const accounts = discoverySource === "synthetic" && discoveredAccounts.length > 0
  ? sampleAccounts
  : storedAccounts
const selectionBelongsToCurrentUser = selectedAccountOwnerId === String(user?.id ?? "")
const personalDataAccounts = selectedAccountId
  ? selectionBelongsToCurrentUser
    ? (dataMap?.accounts ?? []).filter((account) => String(account.account_id) === selectedAccountId)
    : []
  : dataMap?.accounts ?? []
const selectedPersonalAccountMissing = Boolean(
  selectedAccountId && !dataMapLoading && !dataMapError &&
  (!selectionBelongsToCurrentUser || !(dataMap?.accounts ?? []).some((account) => String(account.account_id) === selectedAccountId)),
)

  const filteredAccounts = accounts.filter(
    (account) =>
      (filter === "All" || account.status === filter) &&
      account.name.toLowerCase().includes(search.toLowerCase()),
  )

const setDecision = async (id: number | string, status: string) => {
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
    let actionId: number | string | null = item.actionId

    // Create a pending action if this recommendation has none.
    if (actionId === null) {
      const created = await apiPost<CreateActionResponse>(
        `/privacy-actions/${userId}`,
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

      if (status === "Under review") {
        setAuditLogs(await apiGet<AuditLogsResponse>(`/audit-logs/${userId}`))
        return
      }
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
      `/privacy-actions/${userId}/${actionId}/review`,
      { decision },
    )
    setAuditLogs(await apiGet<AuditLogsResponse>(`/audit-logs/${userId}`))

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

const analyzeAccount = async (accountId: number | string) => {
  const key = String(accountId)
  setAnalysisBusyId(key)
  setActionError(null)
  try {
    const result = await apiPost<AccountAnalysisResponse>(
      `/analysis/${userId}/accounts/${encodeURIComponent(key)}`,
      {},
    )
    setAnalysisByAccount((current) => ({ ...current, [key]: result }))
  } catch (error) {
    setActionError(error instanceof Error ? error.message : "Analysis could not be completed.")
  } finally {
    setAnalysisBusyId(null)
  }
}

const createDeletionDraft = async (accountId: number | string) => {
  const key = String(accountId)
  setDraftBusyId(key)
  setActionError(null)
  try {
    const draft = await apiPost<DeletionDraft>(
      `/privacy-actions/${userId}/accounts/${encodeURIComponent(key)}/deletion-draft`,
      {},
    )
    setDeletionDrafts((current) => ({ ...current, [key]: draft }))
    setActionMessage("Deletion request draft saved for approval. It has not been sent.")
    setAuditLogs(await apiGet<AuditLogsResponse>(`/audit-logs/${userId}`))
  } catch (error) {
    setActionError(error instanceof Error ? error.message : "Draft could not be created.")
  } finally {
    setDraftBusyId(null)
  }
}

const decideDeletionDraft = async (draft: DeletionDraft, decision: "APPROVE" | "REJECT") => {
  const key = String(draft.account_id)
  setDraftBusyId(key)
  setActionError(null)
  try {
    const result = await apiPost<{ status: string; message: string }>(
      `/privacy-actions/${userId}/${encodeURIComponent(String(draft.id))}/review`,
      { decision },
    )
    setDeletionDrafts((current) => ({
      ...current,
      [key]: {
        ...draft,
        status: result.status,
        request_status: result.status === "APPROVED" ? "APPROVED_NOT_SENT" : "REJECTED",
      },
    }))
    setActionMessage(result.status === "APPROVED" ? draft.channel_type === "official_email" ? "Draft approved. It has not been sent; review the destination and choose Send via Gmail." : "Draft approved. It has not been sent; use the official self-service guide or channel." : "Draft rejected. It was not sent.")
    setAuditLogs(await apiGet<AuditLogsResponse>(`/audit-logs/${userId}`))
  } catch (error) {
    setActionError(error instanceof Error ? error.message : "Draft decision could not be saved.")
  } finally {
    setDraftBusyId(null)
  }
}

const sendApprovedDeletionDraft = async (draft: DeletionDraft) => {
  if (!draft.channel_email || draft.channel_type !== "official_email") return
  const confirmed = window.confirm(
    `Send this approved deletion request to ${draft.channel_email} using your connected Gmail account? Confirm that the connected sender address identifies the account you want reviewed.`,
  )
  if (!confirmed) return
  const key = String(draft.account_id)
  setDraftBusyId(key)
  setActionError(null)
  try {
    const result = await apiPost<{ request_status: string; reply_status: string; message: string }>(
      `/privacy-actions/${userId}/${encodeURIComponent(String(draft.id))}/send`,
      {},
    )
    setDeletionDrafts((current) => ({
      ...current,
      [key]: { ...draft, request_status: result.request_status, reply_status: result.reply_status },
    }))
    setActionMessage(result.message)
    setAuditLogs(await apiGet<AuditLogsResponse>(`/audit-logs/${userId}`))
  } catch (error) {
    try {
      const latest = await apiGet<PrivacyActionsResponse>(`/privacy-actions/${userId}`)
      const saved = latest.actions.find((action) => String(action.id) === String(draft.id))
      if (saved) {
        setDeletionDrafts((current) => ({
          ...current,
          [key]: {
            ...draft,
            status: saved.status,
            request_status: saved.request_status ?? draft.request_status,
            reply_status: saved.reply_status ?? draft.reply_status,
          },
        }))
      }
    } catch {
      // Keep the original send error visible if the status refresh also fails.
    }
    setActionError(error instanceof Error ? error.message : "The approved request could not be sent.")
  } finally {
    setDraftBusyId(null)
  }
}

const trackDeletionRequest = async (draft: DeletionDraft, status: "SENT_BY_USER" | "REPLY_RECEIVED") => {
  const key = String(draft.account_id)
  setDraftBusyId(key)
  try {
    const result = await apiPost<{ request_status: string; reply_status: string; message: string }>(
      `/privacy-actions/${userId}/${encodeURIComponent(String(draft.id))}/tracking`,
      { status, reply_note: status === "REPLY_RECEIVED" ? replyNotes[key] : undefined },
    )
    setDeletionDrafts((current) => ({
      ...current,
      [key]: { ...draft, request_status: result.request_status, reply_status: result.reply_status },
    }))
    setActionMessage(result.message)
    const logs = await apiGet<AuditLogsResponse>(`/audit-logs/${userId}`)
    setAuditLogs(logs)
  } catch (error) {
    setActionError(error instanceof Error ? error.message : "Request status could not be saved.")
  } finally {
    setDraftBusyId(null)
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
    <main className={`dashboard dashboard--${tab.toLowerCase().replace(/\s+/g, "-")}`}>
      <aside className="sidebar">
        <div className="sidebar__top">
          <span>{user?.name ? `${user.name.toUpperCase()}’S WORKSPACE` : "SIGNED-IN WORKSPACE"}</span>
          <strong>{tab}</strong>
        </div>
        <nav>
          {nav.map((item, i) => (
            <button
              className={tab === item ? "active" : ""}
              onClick={() => changeTab(item)}
              key={item}
            >
              <span>{["⌂", "◎", "◫", "↗", "≡", "⚙"][i]}</span>
              {item}
            </button>
          ))}
        </nav>
        <div className="sidebar__notice">
          <span>DATA SOURCE</span>
          <p>Inventory records are user-specific. Gmail evidence and synthetic samples are labeled separately.</p>
        </div>
        <button className="sidebar__settings" onClick={onLogout}>
          <span>↪</span> Log out
        </button>
      </aside>
      <div className="dash-content">
        <div className="mobile-tabs" aria-label="Dashboard sections">
          {nav.map((item) => (
            <button
              className={tab === item ? "active" : ""}
              onClick={() => changeTab(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="dash-heading">
          <div>
            <Label>PRIVORA / {user?.name ? user.name.toUpperCase() : "DEMO SESSION"}</Label>
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
            <div className="my-accounts-controls">
              <div className="my-accounts-actions">
              <button
                type="button"
                className="scan-button"
                onClick={() => void loadDiscoveredAccounts("synthetic")}
                disabled={discoveryLoading}
              >
                {discoveryLoading && discoverySource === "synthetic"
                  ? "Loading samples..."
                  : "Load synthetic samples"}
              </button>
              <button
                type="button"
                className="scan-button"
                onClick={() => void connectGmail()}
              >
                Connect Gmail
              </button>
              <button
                type="button"
                className="scan-button"
                onClick={() => void loadDiscoveredAccounts("gmail")}
                disabled={discoveryLoading}
              >
                {discoveryLoading && discoverySource === "gmail"
                  ? "Scanning headers..."
                  : "Discover Gmail"}
              </button>
              </div>
              <p className="my-accounts-status" role="status" aria-live="polite">
                Gmail authorization: {gmailStatus === "authorization_ready"
                  ? "saved; run a scan to verify Gmail API access"
                  : gmailStatus === "not_connected"
                    ? "not connected"
                    : gmailStatus === "reconnect_required"
                      ? "reconnect required"
                      : gmailStatus === "configuration_error"
                        ? "backend configuration error"
                        : gmailStatus === "temporarily_unavailable"
                          ? "temporarily unavailable"
                          : gmailStatus === "unavailable"
                            ? "status unavailable"
                            : "checking…"}
              </p>
            </div>
          )}
        </div>

        {actionError && <p role="alert" className="discovery-error">{actionError}</p>}
        {actionMessage && <p role="status">{actionMessage}</p>}
        {tab === "My Accounts" && dormancyLoading && <p role="status">Reviewing recorded activity dates…</p>}
        {tab === "My Accounts" && dormancyError && <p role="alert">Dormancy status unavailable: {dormancyError}</p>}

        {tab === "Overview" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

            <div className="metrics">
              {[
                [String(dataMap?.account_count ?? 0), "ACCOUNTS IN INVENTORY", "FIRESTORE RECORDS"],
                [String(rules?.recommendations.filter((item) => item.recommendation === "REVIEW").length ?? 0), "NEEDING REVIEW", "RECORDED-DATA RULES"],
                [String(recommendations.filter((item) => item.status === "Pending approval").length), "PENDING APPROVAL", "AWAITING YOUR DECISION"],
                ["0", "CONFIRMED DELETIONS", "NO PROVIDER CONFIRMATIONS RECORDED"],
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
                  <button onClick={() => changeTab("My Accounts")}>
                    View all <Arrow />
                  </button>
                </div>
                <div className="account-list">
                  {accounts.slice(0, 3).map((account) => (
                    <AccountRow account={account} onViewDetails={openAccountDetails} key={account.id} />
                  ))}
                </div>
              </section>
              <RecommendationPanel
                items={recommendations}
                setDecision={setDecision}
                actionError={actionError}
                actionMessage={actionMessage}
                loading={rulesLoading}
                loadError={rulesError}
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
            {discoveryError && (
              <p role="alert" className="discovery-error">
                Discovery failed: {discoveryError}
              </p>
            )}
            <div className="demo-banner">
              <strong>
                {!discoveryRan
                  ? "DISCOVERY NOT RUN"
                  : discoverySource === "gmail"
                    ? "GMAIL HEADER EVIDENCE"
                    : "SYNTHETIC DISCOVERY RESULTS"}
              </strong>
              <span>
                {discoveryRan && discoveredAccounts.length > 0
                  ? discoverySource === "gmail"
                    ? `${discoveredAccounts.length} candidates inferred from Gmail headers and added to the Firestore inventory. These are not verified provider accounts; email evidence is not proof of account activity.`
                    : `${discoveredAccounts.length} synthetic test accounts loaded. These are not verified accounts from your Gmail.`
                  : discoveryRan
                    ? discoverySource === "gmail" ? "The authorized Gmail scan returned no candidate accounts." : "Synthetic sample discovery returned no results."
                    : "No discovery has been run. Connect Gmail for authorized header discovery, or load labeled synthetic samples."}
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
                {["All", "Active", "Dormant", "Status unknown"].map((x) => (
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
              <span>WEBSITE / DOMAIN</span>
              <span>LAST ACTIVITY / EVIDENCE</span>
              <span>ACCOUNT STATUS</span>
              <span />
            </div>
            {discoveryLoading && (
              <p role="status">{discoverySource === "gmail" ? "Scanning authorized Gmail headers and saving candidates…" : "Loading explicitly synthetic accounts…"}</p>
            )}
            {dataMapLoading && discoveredAccounts.length === 0 && <p role="status">Loading saved account inventory…</p>}
            {!dataMapLoading && !discoveryLoading && !discoveryError && accounts.length === 0 && (
              <p>No accounts are stored in this inventory yet. Connect Gmail and run an authorized scan, or load explicitly labeled synthetic samples.</p>
            )}
            {filteredAccounts.map((account) => (
              <AccountRow account={account} detailed onViewDetails={openAccountDetails} key={account.id} />
            ))}
            {!discoveryLoading && accounts.length > 0 && filteredAccounts.length === 0 && (
              <p>No accounts match your search and selected filter.</p>
            )}
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

            {!dataMapLoading && selectedPersonalAccountMissing && (
              <p role="status">
                The selected account is not in this user's stored inventory. Synthetic samples and Gmail header candidates without a stored record do not have personal-data records to show.
              </p>
            )}

            {!dataMapLoading && !selectedAccountId &&
              !dataMapError &&
              dataMap?.accounts.length === 0 && (
                <p>No account records were found for this user.</p>
              )}

            {personalDataAccounts.map((account, index) => (
              <section className="data-card" key={account.account_id}>
                <span>{String(index + 1).padStart(2, "0")}</span>

                <h2>{account.service}</h2>

                <div className="data-card__content">
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
                    Last verified activity
                    <em>
                      {account.last_activity
                        ? new Date(account.last_activity).toLocaleString()
                        : "Not recorded; email evidence is not activity proof"}
                    </em>
                  </p>

                  {account.last_evidence_at && (
                    <p>
                      Last email evidence
                      <em>{new Date(account.last_evidence_at).toLocaleString()}</em>
                    </p>
                  )}

                  <p>
                    Service purpose
                    <em>{account.purpose ?? "Not documented in Privora's service catalog"}</em>
                  </p>
                  {account.purpose_source_url && (
                    <p>
                      Purpose source
                      <em><a href={account.purpose_source_url} target="_blank" rel="noreferrer">Official service documentation</a></em>
                    </p>
                  )}

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

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="scan-button"
                      disabled={analysisBusyId === String(account.account_id)}
                      onClick={() => void analyzeAccount(account.account_id)}
                    >
                      {analysisBusyId === String(account.account_id) ? "Analyzing…" : "Analyze recorded data"}
                    </button>
                    <button
                      type="button"
                      className="scan-button"
                      disabled={draftBusyId === String(account.account_id)}
                      onClick={() => void createDeletionDraft(account.account_id)}
                    >
                      {draftBusyId === String(account.account_id) ? "Saving draft…" : "Draft deletion request"}
                    </button>
                  </div>
                  <small>Mock/local analysis uses this account's stored categories, activity, and discovery evidence. No AI provider is contacted; recorded data does not verify what the service currently holds.</small>

                  {analysisByAccount[String(account.account_id)] && (() => {
                    const analysis = analysisByAccount[String(account.account_id)]
                    return (
                      <div className="demo-banner data-card__analysis" role="status">
                        <strong>
                          {analysis.analysis_mode === "mock_local"
                            ? "MOCK / LOCAL ANALYSIS"
                            : analysis.analysis_mode === "rules_fallback"
                              ? "LOCAL RULES FALLBACK"
                              : "LOCAL RULES ANALYSIS"}
                        </strong>
                        <span>{analysis.explanation}</span>
                        {analysis.fallback_reason && <span>{analysis.fallback_reason}</span>}
                        <span>
                          Sensitivity: {analysis.sensitivity.sensitivity}; flagged: {analysis.sensitivity.sensitive_categories.join(", ") || "none"}. {analysis.limitations}
                        </span>
                        <span>Evidence: {analysis.evidence_note} Source: {analysis.discovery_source}; confidence: {analysis.evidence_confidence}{analysis.last_evidence_at ? `; last evidence ${analysis.last_evidence_at}` : "; evidence time not recorded"}.</span>
                      </div>
                    )
                  })()}

                  {deletionDrafts[String(account.account_id)] && (() => {
                    const draft = deletionDrafts[String(account.account_id)]
                    return (
                      <div className="demo-banner data-card__draft" aria-label="Deletion request draft">
                        <strong>DELETION REQUEST / {draft.request_status}</strong>
                        <span>{draft.subject}</span>
                        {draft.channel_url && draft.channel_catalogued ? (
                          <>
                            <a href={draft.channel_url} target="_blank" rel="noreferrer">
                              {draft.channel_type === "official_self_service_guide" ? "Open official account-closure guide" : "Open catalogued request channel"}
                            </a>
                            {draft.channel_source_url && draft.channel_source_url !== draft.channel_url && <a href={draft.channel_source_url} target="_blank" rel="noreferrer">View source</a>}
                            {draft.channel_type === "official_self_service_guide" && <span>Official self-service guidance. Privora cannot submit account closure for this service.</span>}
                          </>
                        ) : draft.channel_type === "official_email" && draft.channel_email ? (
                          <span>Source-verified deletion-request email: {draft.channel_email}.</span>
                        ) : (
                          <span>No deletion channel is catalogued. Find the official contact channel on the service website before sending.</span>
                        )}
                        {draft.channel_type === "official_email" && draft.channel_email && <span>Sending destination: {draft.channel_email}. Source: <a href={draft.channel_source_url ?? undefined} target="_blank" rel="noreferrer">official service page</a>.</span>}
                        <pre className="data-card__draft-body" aria-label="Deletion request draft text">{draft.body}</pre>
                        {draft.status === "PENDING" && (
                          <div className="flex flex-wrap gap-2">
                            <button type="button" onClick={() => void decideDeletionDraft(draft, "APPROVE")}>Approve draft only — not sent</button>
                            <button type="button" onClick={() => void decideDeletionDraft(draft, "REJECT")}>Reject draft</button>
                          </div>
                        )}
                        {draft.status === "APPROVED" && draft.request_status === "APPROVED_NOT_SENT" && (
                          draft.channel_type === "official_email" ? (
                            <button type="button" disabled={draftBusyId === String(account.account_id)} onClick={() => void sendApprovedDeletionDraft(draft)}>{draftBusyId === String(account.account_id) ? "Sending…" : "Send approved request via Gmail"}</button>
                          ) : (
                            <button type="button" onClick={() => void trackDeletionRequest(draft, "SENT_BY_USER")}>I sent this request externally</button>
                          )
                        )}
                        {draft.request_status === "SEND_UNCONFIRMED" && (
                          <>
                            <p role="alert">Gmail's result was uncertain. Do not send again until you check the Gmail Sent folder.</p>
                            <button type="button" onClick={() => void trackDeletionRequest(draft, "SENT_BY_USER")}>I verified this request appears in Sent</button>
                          </>
                        )}
                        {(draft.request_status === "SENT_BY_USER" || draft.request_status === "SENT_BY_PRIVORA") && (
                          <>
                            {draft.request_status === "SENT_BY_PRIVORA" && <span>Gmail confirmed submission. Provider receipt or account deletion is not confirmed.</span>}
                            {draft.reply_status === "REPLY_CANDIDATE" && <p role="status">Possible reply matched from Gmail message headers in this thread. Review the message in Gmail before confirming.</p>}
                            <label>
                              <span>Optional brief reply summary (do not paste sensitive contents)</span>
                              <input
                                value={replyNotes[String(account.account_id)] ?? ""}
                                maxLength={1000}
                                onChange={(event) => setReplyNotes((current) => ({ ...current, [String(account.account_id)]: event.target.value }))}
                              />
                            </label>
                            <button type="button" onClick={() => void trackDeletionRequest(draft, "REPLY_RECEIVED")}>{draft.reply_status === "REPLY_CANDIDATE" ? "Confirm reply received" : "Record a reply received"}</button>
                          </>
                        )}
                        {draft.request_status === "REPLY_RECEIVED" && <span>Reply recorded as user-reported. Privora has not verified its contents.</span>}
                      </div>
                    )
                  })()}
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
    loading={rulesLoading}
    loadError={rulesError}
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
                placeholder={user?.name || "Your full name"}
              />
              <Field
                label="EMAIL ADDRESS"
                name="settings-email"
                type="email"
                placeholder={user?.email || "you@example.com"}
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
            <button className="logout-button" onClick={onLogout}>
              Log out
            </button>
          </motion.section>
        )}
      </div>
      <Chat
        userId={user?.id}
        accounts={dataMap?.accounts ?? []}
        selectedAccountId={selectedAccountId && selectionBelongsToCurrentUser ? selectedAccountId : null}
      />
    </main>
  )
}

type Account = {
  id: string | number
  icon: string
  name: string
  category: string
  status: string
  data: string
  purpose: string | null
  sourceLabel: string
  lastEvidence: string
}

const AccountRow = ({
  account,
  detailed = false,
  onViewDetails,
}: {
  account: Account
  detailed?: boolean
  onViewDetails?: (accountId: number | string) => void
}) =>
  detailed ? (
    <div className="account-table">
      <div className="account-name">
        <i>{account.icon}</i>
        <strong>{account.name}</strong>
      </div>
      <span>{account.category}<small>{account.sourceLabel}</small></span>
      <span>{account.data}</span>
      <span>{account.lastEvidence}</span>
      <em className={account.status === "Dormant" ? "review" : ""}>
        {account.status}
      </em>
      <button type="button" onClick={() => onViewDetails?.(account.id)}>View details</button>
    </div>
  ) : (
    <div className="account">
      <i>{account.icon}</i>
      <div>
        <strong>{account.name}</strong>
        <span>
          {account.category} · {account.data} · {account.sourceLabel}
        </span>
      </div>
      <em className={account.status === "Dormant" ? "review" : ""}>
        {account.status}
      </em>
      <button type="button" aria-label={`View ${account.name} details`} onClick={() => onViewDetails?.(account.id)}>
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
  loading,
  loadError,
}: {
  items: Recommendation[]
  setDecision: (id: number | string, status: string) => Promise<void>
  standalone?: boolean
  actionError?: string | null
  actionMessage?: string | null
  loading?: boolean
  loadError?: string | null
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
        <Label>RECORDED-DATA RULES</Label>
        <h2>Recommendations to review</h2>
      </div>
      <span className="demo-tag">NOT EXECUTED</span>
    </div>
    <p className="recommendations__privacy-note">
      Local rules use recorded account activity, data categories, and saved policies to suggest KEEP or REVIEW. No action is carried out automatically.
    </p>
    {actionError && <p role="alert">{actionError}</p>}
    {actionMessage && <p role="status">{actionMessage}</p>}
    {loading && <p role="status">Loading recommendations…</p>}
    {loadError && <p role="alert">Recommendations unavailable: {loadError}</p>}
    {!loading && !loadError && items.length === 0 && <p>No recommendations yet. Add an account or recorded activity to generate a review.</p>}
    {items.map((item) => (
      <motion.div className="recommendation" key={item.id} layout>
        <div className="recommendation__body">
          <strong>{item.decision} — {item.account}</strong>
          <p>
            <b>Reason:</b> {item.why}
          </p>
          <p>
            <b>Data:</b> {item.dataContext}
          </p>
          {item.evidenceNote && <p><b>Evidence:</b> {item.evidenceNote}</p>}
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

type AccountChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  mode?: string
  created_at: string
}

const Chat = ({
  userId,
  accounts,
  selectedAccountId,
}: {
  userId: number | string | undefined
  accounts: DataMapResponse["accounts"]
  selectedAccountId: string | null
}) => {
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [input, setInput] = useState("")
  const [accountId, setAccountId] = useState("")
  const selectedAccountIdRef = useRef(accountId)
  const [messages, setMessages] = useState<AccountChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectAccount = useCallback((nextAccountId: string) => {
    selectedAccountIdRef.current = nextAccountId
    setAccountId(nextAccountId)
  }, [])

  useEffect(() => {
    if (!selectedAccountId) return
    selectAccount(
      accounts.some((account) => String(account.account_id) === selectedAccountId)
        ? selectedAccountId
        : "",
    )
  }, [selectedAccountId, accounts, selectAccount])

  useEffect(() => {
    if (selectedAccountId) return
    if (!accountId && accounts.length) selectAccount(String(accounts[0].account_id))
    if (accountId && !accounts.some((account) => String(account.account_id) === accountId)) {
      selectAccount(accounts[0] ? String(accounts[0].account_id) : "")
    }
  }, [accountId, accounts, selectedAccountId, selectAccount])

  useEffect(() => {
    if (userId === undefined || !accountId) {
      setMessages([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    apiGet<{ messages: AccountChatMessage[] }>(
      `/assistant/${encodeURIComponent(String(userId))}/accounts/${encodeURIComponent(accountId)}/messages`,
    )
      .then((result) => { if (!cancelled) setMessages(result.messages) })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "Conversation could not be loaded.")
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [userId, accountId])

  const send = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !accountId || userId === undefined || sending) return
    const text = input
    const submittedAccountId = accountId
    setSending(true)
    setError(null)
    setInput("")
    try {
      const response = await apiPost<{ mode: string; messages: AccountChatMessage[] }>(
        `/assistant/${encodeURIComponent(String(userId))}/accounts/${encodeURIComponent(submittedAccountId)}/messages`,
        { message: text },
      )
      if (selectedAccountIdRef.current === submittedAccountId) {
        setMessages((current) => [...current, ...response.messages])
      }
    } catch (sendError) {
      if (selectedAccountIdRef.current === submittedAccountId) {
        setError(sendError instanceof Error ? sendError.message : "Message could not be processed.")
        setInput(text)
      }
    } finally {
      setSending(false)
    }
  }
  const latestAssistantMode = [...messages]
    .reverse()
    .find((message) => message.role === "assistant")?.mode
  return (
    <div className="chat-wrap">
      <AnimatePresence>
        {open && (
          <motion.div
            className={`chat ${expanded ? "chat--expanded" : ""}`}
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
                    <strong>PRIVORA ASSISTANT</strong>
                    <small>{latestAssistantMode === "mock_local" ? "MOCK / LOCAL MODE" : latestAssistantMode === "nvidia_nemotron" ? "HISTORICAL NVIDIA RESPONSE" : latestAssistantMode === "rules_fallback" ? "LOCAL RULES MODE" : "SAVED / RULES MODE"}</small>
                </span>
              </div>
              <div className="chat__head-actions">
                <button type="button" onClick={() => setExpanded((value) => !value)} aria-label={expanded ? "Return chat to compact size" : "Expand chat"}>{expanded ? "↙" : "↗"}</button>
                <button type="button" onClick={() => { setOpen(false); setExpanded(false) }} aria-label="Minimize chat">×</button>
              </div>
            </div>
            <div className="chat__messages">
              {loading && <p role="status">Loading this account's conversation…</p>}
              {error && <p role="alert">{error}</p>}
              {!loading && messages.length === 0 && <p>Ask about this account's discovered evidence, recorded and inferred data categories, activity, privacy concerns, or local recommendation. Replies use mock/local rules and no AI provider is called.</p>}
              {messages.map((message) => (
                <div className={`message message--${message.role}`} key={message.id}>
                  {message.role === "assistant" && message.mode && (
                    <small className="message__mode">
                      {message.mode === "mock_local" ? "MOCK / LOCAL RESPONSE" : message.mode === "nvidia_nemotron" ? "HISTORICAL NVIDIA RESPONSE" : message.mode === "rules_fallback" ? "LOCAL RULES RESPONSE" : "LOCAL RULES RESPONSE"}
                    </small>
                  )}
                  {message.content}
                </div>
              ))}
            </div>
            <label className="chat__account">
              <span>ACCOUNT CONTEXT</span>
              <select value={accountId} onChange={(event) => selectAccount(event.target.value)} disabled={!accounts.length}>
                {accounts.map((account) => <option value={String(account.account_id)} key={account.account_id}>{account.service}</option>)}
              </select>
            </label>
            <small className="chat__privacy-note">Mock/local responses use this account's stored context and local rules. No chat text or account data is sent to an AI provider for these responses.</small>
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
                disabled={!accountId || sending}
              />
              <button aria-label="Send" disabled={!accountId || sending}>
                <Arrow />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        className="chat-trigger"
        onClick={() => setOpen(!open)}
        aria-label={open ? "Close Privora assistant" : "Open Privora assistant"}
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
  const [view, setView] = useState<View>(() => viewForPath(window.location.pathname))
  const [user, setUser] = useState<UserProfile | null>(null)
  const logout = async () => {
    if (firebaseAuth) await signOut(firebaseAuth)
    setUser(null)
    window.history.replaceState({}, "", routeForView.home)
    setView("home")
  }
  const navigate = (next: View, anchor?: string) => {
    const nextPath = next === "not-found" ? "/404" : routeForView[next]
    if (window.location.pathname !== nextPath) window.history.pushState({}, "", nextPath)
    setView(next)
    window.scrollTo({ top: 0, behavior: "smooth" })
    if (anchor) setTimeout(() => document.getElementById(anchor)?.scrollIntoView({ behavior: "smooth" }), 50)
  }
  useEffect(() => {
    const handlePopState = () => setView(viewForPath(window.location.pathname))
    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [])
  useEffect(() => {
    const titles: Record<View, string> = {
      home: "Privora — Your Digital Life. Your Control.",
      privacy: "Privacy Policy — Privora",
      terms: "Terms of Service — Privora",
      "not-found": "Page Not Found — Privora",
      login: "Privora — Login",
      signup: "Privora — Signup",
      onboarding: "Privora — Onboarding",
      dashboard: "Privora — Dashboard",
    }
    document.title =
      titles[view]
    const description = view === "privacy"
      ? "Privacy information for Privora, including Gmail metadata use and current data controls."
      : view === "terms"
        ? "Draft terms describing how Privora works and its current limitations."
        : "Privora helps organize account candidates and review a personal digital footprint."
    let descriptionTag = document.querySelector<HTMLMetaElement>('meta[name="description"]')
    if (!descriptionTag) {
      descriptionTag = document.createElement("meta")
      descriptionTag.name = "description"
      document.head.appendChild(descriptionTag)
    }
    descriptionTag.content = description
  }, [view])
  useEffect(() => {
    if (!firebaseAuth) return
    return onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
      if (!firebaseUser) {
        setUser(null)
        return
      }
      try {
        const profile = await apiGet<UserProfile>("/auth/me")
        setUser(profile)
        setView((current) => {
          if (current === "home") {
            window.history.replaceState({}, "", routeForView.dashboard)
            return "dashboard"
          }
          return current
        })
      } catch {
        setUser(null)
      }
    })
  }, [])
  return (
    <div className="app">
      {view !== "onboarding" && <Header view={view} navigate={navigate} user={user} />}
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
            <Auth mode={view} navigate={navigate} onAuthenticated={setUser} />
          )}
          {view === "onboarding" && <Onboarding navigate={navigate} />}
          {(view === "privacy" || view === "terms") && (
            <>
              <LegalPage kind={view as LegalPageKind} navigateHome={() => navigate("home")} />
              <Footer navigate={navigate} />
            </>
          )}
          {view === "not-found" && (
            <main className="legal-page legal-page--not-found">
              <h1>Page not found</h1>
              <p>This Privora page does not exist.</p>
              <button className="legal-page__back" onClick={() => navigate("home")}>Back to Privora home</button>
            </main>
          )}
          {view === "dashboard" && (
            <Dashboard key={user?.uid ?? "anonymous"} navigate={navigate} user={user} onLogout={() => void logout()} />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
