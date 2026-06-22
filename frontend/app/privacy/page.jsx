// frontend/app/privacy/page.jsx

import Link from 'next/link';
import { Sparkles, ArrowLeft } from 'lucide-react';
import '@/styles/landing.css';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata = {
  title: 'Privacy Policy',
  description: 'NeuralCore Privacy Policy — how we collect, use, and protect your data.',
};

const SECTIONS = [
  {
    title: '1. Information We Collect',
    body: `We collect information you provide directly: account registration data (name, email, organization name), payment information processed by our payment providers (Stripe, Razorpay, PayPal — we do not store raw card data), and content you upload or create within the Platform including documents, prompts, and knowledge base data.\n\nWe automatically collect usage data: access logs, API request metadata, performance metrics, error reports, and feature usage analytics. This data is used solely to improve Platform reliability and performance.\n\nWe do not collect biometric data, location data, or sensitive personal information beyond what is necessary to provide the service.`,
  },
  {
    title: '2. How We Use Your Information',
    body: `Your information is used to: provide and operate the Platform; process transactions and send billing notifications; send security alerts and critical service updates; improve platform performance and reliability; respond to support requests.\n\nWe do not sell, rent, or trade your personal information or Customer Data to third parties for their marketing purposes.`,
  },
  {
    title: '3. Customer Data and Tenant Isolation',
    body: `"Customer Data" refers to all data you upload, ingest, or generate within the Platform — documents, embeddings, knowledge bases, agent configurations, and outputs. Customer Data is fully isolated between tenants at the database, vector store, cache, and agent runtime layers. No other tenant can access your Customer Data through normal or adversarial use of the Platform.\n\nYou retain full ownership of your Customer Data. We process it only as instructed by your use of the Platform features.`,
  },
  {
    title: '4. Data Retention',
    body: `Active account data is retained as long as your account remains active. Upon account deletion or contract termination, Customer Data is available for export for 30 days and then permanently deleted from all storage systems including vector databases, object storage, and backups within 90 days.\n\nUsage logs and anonymized analytics may be retained for up to 2 years for performance monitoring and security auditing.`,
  },
  {
    title: '5. Data Security',
    body: `We implement industry-standard security measures: TLS 1.3 for all data in transit; AES-256 encryption for data at rest; bcrypt-hashed credentials; JWT RS256 signing with short-lived tokens; role-based access control with 5 privilege levels; comprehensive audit logging of all significant operations; PII detection and configurable redaction in document ingestion pipelines; dependency vulnerability scanning in CI/CD.\n\nNo security system is 100% guaranteed. We encourage responsible disclosure of security vulnerabilities to sambhavdwivedi@outlook.com.`,
  },
  {
    title: '6. Third-Party Services',
    body: `The Platform integrates with third-party services at your direction, including: LLM providers (OpenAI, Anthropic, Google, etc.); payment processors (Stripe, Razorpay, PayPal); vector database services; cloud infrastructure providers. Your use of these integrations is subject to their respective privacy policies. We are not responsible for the privacy practices of third-party services.`,
  },
  {
    title: '7. Cookies and Tracking',
    body: `We use a single authentication cookie ("nc_access_token") required for Platform operation. We do not use third-party tracking cookies, advertising pixels, or behavioral analytics tools beyond anonymous performance monitoring. You can delete the authentication cookie at any time, which will sign you out of the Platform.`,
  },
  {
    title: '8. Your Rights',
    body: `Depending on your jurisdiction, you may have rights to: access a copy of your personal data; correct inaccurate data; delete your account and associated data; export your Customer Data; restrict or object to certain processing; withdraw consent where processing is based on consent.\n\nTo exercise any of these rights, contact us at sambhavdwivedi@outlook.com. We will respond within 30 days.`,
  },
  {
    title: '9. Children\'s Privacy',
    body: `The Platform is not directed to individuals under 18 years of age. We do not knowingly collect personal information from minors. If you believe a minor has provided us with personal information, please contact us immediately.`,
  },
  {
    title: '10. Changes to This Policy',
    body: `We may update this Privacy Policy periodically to reflect changes in our practices or applicable law. We will notify you of material changes at least 14 days in advance via email or in-platform notification. The "Last updated" date at the top of this page indicates when the policy was last revised.`,
  },
  {
    title: '11. Contact Us',
    body: `For privacy-related questions, data requests, or security concerns:\n\nSambhav Dwivedi\nEmail: sambhavdwivedi@outlook.com\nWebsite: https://www.sambhavdwivedi.in`,
  },
];

function renderBodyWithLinks(text) {
  const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/gi;
  const urlRegex = /(https?:\/\/[^\s]+)/gi;
  
  return text.split('\n\n').map((para, i) => {
    let parts = para.split(/(https?:\/\/[^\s]+|[a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+)/gi);
    
    return (
      <p key={i} className="text-sm text-muted-foreground leading-relaxed">
        {parts.map((part, j) => {
          if (part.match(emailRegex)) {
            return (
              <a key={j} href={`mailto:${part}`} className="text-primary hover:underline">
                {part}
              </a>
            );
          }
          if (part.match(urlRegex)) {
            return (
              <a key={j} href={part} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                {part}
              </a>
            );
          }
          return part;
        })}
      </p>
    );
  });
}

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="border-b border-border">
        <div className="landing-container flex h-14 items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold text-foreground">NeuralCore</span>
          </Link>
          <Link href="/" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft className="h-3 w-3" /> Back to home
          </Link>
        </div>
      </div>

      <div className="landing-container px-4 sm:px-6 py-12 sm:py-16 max-w-3xl">
        <div className="flex flex-col gap-2 mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Privacy Policy</h1>
          <p className="text-sm text-muted-foreground">Last updated: June 2026</p>
        </div>

        <div className="flex flex-col gap-8">
          {SECTIONS.map((s) => (
            <div key={s.title} className="flex flex-col gap-2">
              <h2 className="text-base font-semibold text-foreground">{s.title}</h2>
              {renderBodyWithLinks(s.body)}
            </div>
          ))}
        </div>
      </div>

      <LandingFooter />
    </div>
  );
}
