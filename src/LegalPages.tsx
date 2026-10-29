import type { ReactNode } from "react"

export type LegalPageKind = "privacy" | "terms"

const EffectiveDate = () => (
  <p className="legal-page__effective">Draft for review · Effective 28 October 2026</p>
)

const Section = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="legal-page__section">
    <h2>{title}</h2>
    {children}
  </section>
)

const PrivacyPolicy = () => (
  <>
    <header className="legal-page__intro">
      <span className="legal-page__eyebrow">PRIVORA / PRIVACY</span>
      <h1>Privacy Policy</h1>
      <EffectiveDate />
      <p>
        This draft describes how the current Privora application processes
        information. It is based on the code paths reviewed for this release
        preparation and must be checked by the product operator before it is
        published as a final policy.
      </p>
    </header>

    <Section title="What Privora processes">
      <p>
        Firebase Authentication supplies the signed-in user's identifier and,
        where available, name and email address. Privora stores a user profile
        and user-specific records in Cloud Firestore, including account
        candidates, service references, recorded or inferred data categories,
        policies, recommendation-related privacy actions, audit events, and
        account-specific chat messages.
      </p>
      <p>
        The application also stores deletion-request drafts and their review
        status. If a user sends an approved draft through Gmail, Privora records
        the send status and Gmail message/thread identifiers used for later
        reply checks. Draft text can contain information the user chose to
        include.
      </p>
    </Section>

    <Section title="Optional Gmail access">
      <p>
        When a user connects Gmail, Privora requests
        <code> gmail.metadata </code> to scan a bounded number of messages and
        retrieve message identifiers plus sender, subject, and date metadata.
        The current discovery provider does not request message bodies. Local
        keyword rules use the available metadata to identify candidate service
        domains and possible data categories. Results can be incomplete and do
        not prove account ownership, service activity, or what a provider
        currently holds.
      </p>
      <p>
        The same connection flow currently also requests
        <code> gmail.send </code>. That permission is used only for a separate
        user-approved operation: sending a deletion-request draft to a
        source-verified service email after the user approves the draft and
        confirms the send. The resulting Gmail message is delivered to that
        recipient. Privora may later retrieve only sender/date headers from
        that sent thread to show a possible reply; it does not read reply
        bodies. A possible reply is not provider confirmation that a request
        was accepted or completed.
      </p>
      <p>
        Gmail OAuth credentials are stored per Firebase user in Firestore in
        Fernet-encrypted form. Temporary OAuth state and a PKCE verifier are
        stored for the authorization flow and consumed on callback. Other
        Firestore records are not application-encrypted by this code. Google
        processes authentication and Gmail API requests under its own terms
        and policies.
      </p>
      <p className="legal-page__policy-commitment">
        Use of information received from Google Workspace scopes will adhere to
        the Google User Data Policy, including the Limited Use requirements.
        The operator must confirm that this statement matches actual
        operations before publication.
      </p>
    </Section>

    <Section title="How information is used">
      <p>
        Privora uses account and profile information to authenticate users and
        keep their records separated. It uses candidate service details and
        categories to display an inventory, identify missing or older activity
        information, and provide local rule-based KEEP or REVIEW suggestions.
        Privacy Analysis and account chat currently use local rules and
        account context; the registered application routes do not send this
        information to NVIDIA or another AI provider.
      </p>
      <p>
        The repository contains a separate legacy AI module, but it is not
        called by the current analysis, recommendation, or chat routes. No
        analytics or advertising integration is configured in the current
        frontend source. The site loads fonts from Google Fonts, which may
        receive normal browser request information when a page loads.
      </p>
    </Section>

    <Section title="Storage, retention, and choices">
      <p>
        User records and encrypted Gmail credentials are stored in Cloud
        Firestore. The reviewed application does not provide an in-product
        control to disconnect Gmail or delete a Privora account and its stored
        records, and no retention schedule is implemented in the application.
        Revoking Google access can stop future Gmail API access, but the
        encrypted credential record still requires removal from Firestore by
        the operator. Do not treat external account deletion drafts as deletion
        of Privora's own records.
      </p>
      <p>
        Users can review or revoke third-party access in their Google Account
        security settings. Privora's current interface requires a product
        operator to handle requests about Privora-held data; a public contact
        channel has not yet been supplied. A deletion request sent to another
        service does not delete the records Privora holds.
      </p>
    </Section>

    <Section title="Security and sharing">
      <p>
        The backend verifies Firebase ID tokens and checks user ownership
        before serving user-specific records. Gmail OAuth uses state and PKCE,
        and stored Gmail credentials are encrypted by the application before
        they are written to Firestore. These safeguards do not amount to a
        security certification or guarantee. The application shares an
        approved email draft with its intended recipient only when the user
        confirms sending it through Gmail.
      </p>
    </Section>

    <Section title="Children, changes, and contact">
      <p>
        Privora is presented as a tool for people managing their own online
        accounts. The project has not specified a minimum age or a children's
        data process; the operator must settle eligibility before public
        release. If this policy changes, the published version and its
        effective date should be updated before new data uses begin.
      </p>
      <p>
        No public privacy or support email/address is configured in the
        reviewed project. The operator must provide and verify a contact route
        before publication so users can make privacy requests.
      </p>
    </Section>
  </>
)

const TermsOfService = () => (
  <>
    <header className="legal-page__intro">
      <span className="legal-page__eyebrow">PRIVORA / TERMS</span>
      <h1>Terms of Service</h1>
      <EffectiveDate />
      <p>
        These practical draft terms describe the current Privora application.
        They are not legal advice and require review for the operator's
        jurisdiction and business before publication.
      </p>
    </header>

    <Section title="Using Privora">
      <p>
        By using Privora, you agree to use it lawfully and only for accounts
        and information you are authorized to manage. You are responsible for
        protecting your sign-in credentials, reviewing information you add,
        and deciding whether an account or proposed action is yours to manage.
        The project has not yet specified a minimum user age or a legal
        eligibility rule; that must be decided before public release.
      </p>
    </Section>

    <Section title="What the service does">
      <p>
        Privora provides an account inventory, optional Gmail metadata-based
        candidate discovery, local privacy analysis and chat responses,
        rule-based recommendations, and tools to draft and track privacy
        requests. Discovery and categories can be incomplete or incorrect.
        Gmail evidence does not establish ownership, current account activity,
        or a service's current data holdings. Analysis and chat are
        informational and may not reflect a provider's practices.
      </p>
    </Section>

    <Section title="Google access and user decisions">
      <p>
        If you connect Gmail, you authorize the scopes shown on Google's
        consent screen. You can revoke that access through your Google Account
        settings. Privora currently has no in-product Gmail disconnect control;
        revocation does not itself remove encrypted credentials or other
        records already stored by Privora.
      </p>
      <p>
        A privacy or deletion request remains a draft until you approve it.
        Gmail sending requires an additional explicit confirmation. A sent
        status means Gmail accepted the message for submission; it does not
        mean the recipient received, accepted, or completed the request. A
        service provider alone can confirm deletion of its account or retained
        data.
      </p>
    </Section>

    <Section title="Responsible use and third parties">
      <p>
        Do not use Privora to access another person's accounts without
        authorization, interfere with a service, or violate applicable law.
        Google Authentication, Gmail, Firebase, Firestore, and Google Fonts
        are third-party services subject to their own terms and availability.
        Privora does not control their operation.
      </p>
    </Section>

    <Section title="Availability, ownership, and limitations">
      <p>
        Privora is provided as currently available and may change or become
        unavailable. The application makes suggestions, not guarantees, and
        does not itself delete external accounts. To the extent allowed by
        applicable law, the operator disclaims warranties and liability for
        indirect loss arising from use of the application; mandatory legal
        rights are not waived by this draft.
      </p>
      <p>
        Privora's name, interface, and original materials remain with their
        respective rights holders. No legal entity or intellectual-property
        ownership details have been supplied in the project, so the operator
        must confirm those details before publication.
      </p>
    </Section>

    <Section title="Changes and contact">
      <p>
        Updated terms should be published with a revised effective date. The
        operator must provide a valid contact address, identify the service
        operator, and select any governing-law and venue terms with qualified
        legal advice. No public support or legal contact is currently
        configured.
      </p>
    </Section>
  </>
)

export default function LegalPage({
  kind,
  navigateHome,
}: {
  kind: LegalPageKind
  navigateHome: () => void
}) {
  const isPrivacy = kind === "privacy"
  return (
    <main className="legal-page">
      <button className="legal-page__back" type="button" onClick={navigateHome}>
        ← Back to Privora home
      </button>
      {isPrivacy ? <PrivacyPolicy /> : <TermsOfService />}
      <div className="legal-page__draft-note" role="note">
        This is a practical product draft, not a legal certification. Add the
        operator's verified contact details and obtain jurisdiction-specific
        legal review before public launch.
      </div>
    </main>
  )
}
