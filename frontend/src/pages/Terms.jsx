import { Link } from 'react-router-dom'
import { PageHero } from '../components/ui'
import { useDocumentTitle } from '../lib/hooks'

export default function Terms() {
  useDocumentTitle('Terms and Conditions')
  return (
    <>
      <PageHero eyebrow="Terms and Conditions" title="Using Gaon Saathi" lead="Last updated: November 2026. Please read these simple terms before submitting a complaint." />
      <section className="section">
        <div className="container-page">
          <article className="prose-page mx-auto max-w-3xl">
            <h2 className="!mt-0">1. About the service</h2>
            <p>
              Gaon Saathi is an <strong>independent</strong> grievance-support platform. It is not a government website, not a
              government authority and not a law firm. Using Gaon Saathi is free.
            </p>

            <h2>2. What submitting a complaint means</h2>
            <ul>
              <li>By submitting, you allow the Gaon Saathi team to review your complaint and evidence for verification and appropriate follow-up.</li>
              <li>Submitting here is <strong>not</strong> the same as filing an official complaint with the government, a police report or a court case.</li>
              <li>An anonymous submission does not create legal representation or any lawyer-client relationship.</li>
              <li>We decide, after review, whether and where to take a complaint forward. We may decide not to.</li>
              <li>We cannot promise any particular outcome, timeline or government response.</li>
            </ul>

            <h2>3. Your responsibilities</h2>
            <ul>
              <li>Report honestly. Share only what you believe to be true.</li>
              <li>Report problems about public resources and governance, not personal disputes.</li>
              <li>Do not upload content that is illegal, sexually explicit, violent for no reason, or that shows other people's private information.</li>
              <li>Do not use the platform to threaten, harass or make false accusations against anyone.</li>
              <li>Do not try to attack, overload or misuse the platform.</li>
            </ul>

            <h2>4. Our responsibilities</h2>
            <ul>
              <li>We review complaints in good faith and check evidence before acting.</li>
              <li>We show "Forwarded to Relevant Authority" only after we have actually submitted the complaint and recorded the submission details.</li>
              <li>We do not invent government responses and do not mark complaints as resolved without a real update.</li>
              <li>We protect your data as explained in our <Link to="/privacy">Privacy Policy</Link>.</li>
            </ul>

            <h2>5. Removing content</h2>
            <p>We may reject, close or delete complaints that are spam, abusive, clearly false or outside the purpose of the platform.</p>

            <h2>6. Emergencies</h2>
            <p>Gaon Saathi is not an emergency service. If anyone is in immediate danger, call <strong>112</strong>.</p>

            <h2>7. Limitation of liability</h2>
            <p>
              The platform is provided "as is". To the extent allowed by law, Gaon Saathi is not responsible for actions or
              decisions taken by government authorities or third parties, or for loss caused by information you choose to share.
            </p>

            <h2>8. Changes</h2>
            <p>We may update these terms. The date at the top shows the latest version.</p>
          </article>
        </div>
      </section>
    </>
  )
}
