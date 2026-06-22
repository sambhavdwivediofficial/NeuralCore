// frontend/app/page.jsx

import '@/styles/landing.css';
import { LandingNav } from '@/components/landing/LandingNav';
import { HeroSection } from '@/components/landing/HeroSection';
import { MetricsSection } from '@/components/landing/MetricsSection';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { TechStackSection } from '@/components/landing/TechStackSection';
import { PricingSection } from '@/components/landing/PricingSection';
import { CTASection } from '@/components/landing/CTASection';
import { LandingFooter } from '@/components/landing/LandingFooter';

export const metadata = {
  title: 'NeuralCore — AI Infrastructure Platform',
  description:
    'Production-grade RAG, Agentic AI, Multi-Agent Orchestration, Knowledge Graphs, Fine-Tuning, and Enterprise Multi-Tenancy in one modular platform.',
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <LandingNav />
      <main>
        <HeroSection />
        <MetricsSection />
        <FeaturesSection />
        <TechStackSection />
        <PricingSection />
        <CTASection />
      </main>
      <LandingFooter />
    </div>
  );
}
