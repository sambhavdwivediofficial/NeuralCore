// frontend/app/terms/page.jsx

import Link from 'next/link';
import { Sparkles, ArrowLeft } from 'lucide-react';
import '@/styles/landing.css';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata = {
  title: 'Terms of Service — NeuralCore',
  description: 'NeuralCore Terms of Service agreement.',
};

const SECTIONS = [
  {
    title: '1. Acceptance of Terms',
    body: `By accessing or using NeuralCore ("the Platform"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to all of these Terms, you may not use the Platform. These Terms apply to all users, including free trial users, paid subscribers, and enterprise customers.`,
  },
  {
    title: '2. Description of Service',
    body: `NeuralCore is an enterprise AI infrastructure platform providing Retrieval-Augmented Generation (RAG), Agentic AI orchestration, multi-agent systems, knowledge management, model fine-tuning, and related capabilities. The Platform is provided as a software-as-a-service (SaaS) offering and may also be self-hosted under applicable license terms.`,
  },
  {
    title: '3. Account Registration',
    body: `You must create an account to access the Platform. You are responsible for maintaining the confidentiality of your credentials and for all activities that occur under your account. You agree to notify us immediately at sambhavdwivedi@outlook.com of any unauthorized use of your account. We reserve the right to terminate accounts that violate these Terms.`,
  },
  {
    title: '4. Acceptable Use',
    body: `You agree not to use the Platform to: (a) violate any applicable laws or regulations; (b) infringe on intellectual property rights; (c) transmit malicious code or interfere with Platform integrity; (d) attempt unauthorized access to any system, network, or account; (e) process data in violation of applicable privacy regulations including GDPR, CCPA, or HIPAA; (f) use the Platform to build competing products without explicit written permission.`,
  },
  {
    title: '5. Data and Privacy',
    body: `You retain ownership of all data you upload, ingest, or generate through the Platform ("Customer Data"). By using the Platform, you grant NeuralCore a limited license to process Customer Data solely for providing the services you request. We do not sell Customer Data. Data handling is governed by our Privacy Policy. Tenant data isolation is enforced at all layers of the Platform architecture.`,
  },
  {
    title: '6. Intellectual Property',
    body: `The Platform, including all software, algorithms, designs, and documentation, is owned by Sambhav Dwivedi and protected under applicable copyright and intellectual property laws. All Rights Reserved. You may not copy, modify, distribute, sell, or lease any part of the Platform without express written permission. Feedback and suggestions you provide may be incorporated into the Platform without obligation.`,
  },
  {
    title: '7. Billing and Payments',
    body: `Paid plans are billed in advance on a monthly or annual basis. You authorize us to charge your payment method on file. Failure to pay may result in service suspension. Refunds are not provided for partial months except where required by applicable law. Enterprise custom agreements supersede these standard billing terms.`,
  },
  {
    title: '8. Service Availability',
    body: `We strive for high availability but do not guarantee uninterrupted access to the Platform. We may perform maintenance, updates, or experience outages beyond our control. We will provide advance notice of planned maintenance where possible. Enterprise SLA commitments are governed by separate agreement.`,
  },
  {
    title: '9. Limitation of Liability',
    body: `To the maximum extent permitted by law, NeuralCore and its developer shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including loss of profits, data, or business opportunities arising from your use of the Platform. Our total liability shall not exceed the amounts paid by you in the twelve months preceding the claim.`,
  },
  {
    title: '10. Indemnification',
    body: `You agree to indemnify and hold harmless NeuralCore and Sambhav Dwivedi from any claims, damages, losses, or expenses (including legal fees) arising from your use of the Platform, your violation of these Terms, or your infringement of any third-party rights.`,
  },
  {
    title: '11. Termination',
    body: `Either party may terminate the agreement with 30 days written notice. We may terminate immediately for material breach, non-payment, or violation of our Acceptable Use policy. Upon termination, your access will be revoked and Customer Data will be available for export for 30 days before deletion.`,
  },
  {
    title: '12. Governing Law',
    body: `These Terms shall be governed by and construed in accordance with the laws of India. Any disputes shall be resolved through binding arbitration in accordance with applicable rules before resorting to litigation.`,
  },
  {
    title: '13. Changes to Terms',
    body: `We may update these Terms periodically. We will notify you of material changes via email or in-platform notification at least 14 days before they take effect. Continued use of the Platform after changes take effect constitutes acceptance of the revised Terms.`,
  },
  {
    title: '14. Contact',
    body: `For questions about these Terms, contact: sambhavdwivedi@outlook.com`,
  },
];

export default function TermsPage() {
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
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Terms of Service</h1>
          <p className="text-sm text-muted-foreground">Last updated: June 2026</p>
        </div>

        <div className="flex flex-col gap-8">
          {SECTIONS.map((s) => (
            <div key={s.title} className="flex flex-col gap-2">
              <h2 className="text-base font-semibold text-foreground">{s.title}</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </div>

      <LandingFooter />
    </div>
  );
}
