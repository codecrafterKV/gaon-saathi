import { Link } from 'react-router-dom'
import { PageHero } from '../components/ui'
import { useDocumentTitle } from '../lib/hooks'

export default function Privacy() {
  useDocumentTitle('Privacy Policy')
  return (
    <>
      <PageHero eyebrow="Privacy Policy" title="How we protect you" lead="Last updated: November 2026. Written in simple English." />
      <section className="section">
        <div className="container-page">
          <article className="prose-page mx-auto max-w-3xl">
            <p>
              Gaon Saathi is built on one idea: <strong>we should not need to know who you are</strong>. This policy explains what
              information the platform handles, what it does not collect, and the limits of what any website can promise.
            </p>

            <h2>1. What we do NOT collect</h2>
            <ul>
              <li>Your name, mobile number, email address, Aadhaar number, home address or photograph.</li>
              <li>Any user account, login or profile. Reporters never register.</li>
              <li>Your IP address. Our application does not store it in the database or in its logs.</li>
              <li>Advertising cookies, analytics, tracking pixels or social media plugins. We use no third-party analytics.</li>
              <li>Original file names of the files you upload (they can contain names or phone numbers).</li>
            </ul>

            <h2>2. What we DO store</h2>
            <ul>
              <li><strong>The problem you report:</strong> category, village, district, state, description and optional approximate location of the problem.</li>
              <li><strong>Evidence you choose to upload:</strong> photos, videos or PDF files, after cleaning (see below).</li>
              <li><strong>Information you add later</strong> through the Track Complaint page.</li>
              <li><strong>Codes:</strong> your Complaint ID, and a one-way keyed hash of your Tracking Code (not the code itself).</li>
              <li><strong>Dates:</strong> when the complaint was submitted and when its status changed.</li>
              <li><strong>Team records:</strong> review notes, verification findings and forwarding details written by our team.</li>
            </ul>

            <h2>3. How we protect it</h2>
            <ul>
              <li>All connections use encryption (HTTPS) in our production setup.</li>
              <li>Complaint descriptions, notes and evidence files are <strong>encrypted when stored</strong> (AES-256-GCM).</li>
              <li>Hidden information such as GPS location and phone model is removed from photos, both on your phone before upload and again on our server. Hidden data is also removed from videos and PDF files where technically possible.</li>
              <li>Evidence is never available through a public link. Only authorised team members, after signing in, can view it. Every view is recorded.</li>
              <li>Team accounts use strong password hashing (Argon2id), session timeouts, login limits and role-based permissions.</li>
              <li>Complaint text and evidence are never written to application logs.</li>
              <li>Anti-spam protection runs in your own browser (a small calculation), instead of a third-party CAPTCHA that could track you.</li>
              <li>Request limits use a short-lived, scrambled form of the network address that is kept only in memory and never saved.</li>
            </ul>

            <h2>4. The limits of anonymity - please read</h2>
            <p>
              We work hard to protect you, but <strong>no website can guarantee complete anonymity</strong>. You could still be identified if:
            </p>
            <ul>
              <li>you write details that only you would know, or mention yourself or your family;</li>
              <li>a photo or video shows your face, your house, your voice or something unique to you;</li>
              <li>someone sees you using your phone, or looks at your browser history on a shared phone;</li>
              <li>your internet provider, network or device keeps its own records (we have no control over these);</li>
              <li>our hosting provider's network equipment briefly processes connection information to deliver the website.</li>
            </ul>
            <p>Describe the problem, not yourself. If you are in danger, call <strong>112</strong>.</p>

            <h2>5. Who can see your complaint</h2>
            <p>
              Only authorised Gaon Saathi team members. If we take a complaint to a government authority, we share the details of
              the problem needed for action (such as the category, location, description and relevant evidence). We cannot share
              your identity, because we do not have it. Anyone with both your Complaint ID and Tracking Code can see the limited
              public status of your complaint (never the description or evidence).
            </p>

            <h2>6. How long we keep data</h2>
            <p>
              Complaints that are resolved, rejected or closed are permanently deleted, together with their evidence, after a
              retention period set by our administrators (365 days by default). Spam or abusive submissions can be deleted earlier.
            </p>

            <h2>7. Demo data</h2>
            <p>
              For demonstrations, the platform can contain sample complaints marked "DEMO". These are fictional and are kept
              separate from real complaints.
            </p>

            <h2>8. Changes and questions</h2>
            <p>
              We will update this page if our practices change. For questions, see the <Link to="/contact">Contact / Support</Link> page.
              Please also read our <Link to="/terms">Terms and Conditions</Link>.
            </p>
          </article>
        </div>
      </section>
    </>
  )
}
