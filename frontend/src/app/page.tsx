"use client";

import Link from "next/link";
import { FileText, ArrowRight, Zap, Target, Shield } from "lucide-react";
import { motion } from "framer-motion";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.container}>
      <nav className={styles.nav}>
        <div className={styles.logo}>
          <FileText size={24} className={styles.logoIcon} />
          JobSeek <span className="gradient-text">AI</span>
        </div>
        <Link href="/login" className={styles.loginBtn}>
          Sign In
        </Link>
      </nav>

      <main className={styles.hero}>
        <div className={styles.heroBg} />
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className={styles.badge}
        >
          ✨ JobSeek AI 1.0 is live
        </motion.div>
        
        <motion.h1 
          className={styles.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          Land your dream job with an <br />
          <span className="gradient-text">ATS-Optimized CV</span>
        </motion.h1>
        
        <motion.p 
          className={styles.subtitle}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          Upload your general resume and paste a job description. Our AI instantly 
          generates a highly targeted, professional CV designed to pass Applicant Tracking Systems.
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <Link href="/login" className={styles.ctaBtn}>
            Get Started Free <ArrowRight size={20} />
          </Link>
        </motion.div>
      </main>

      <section className={styles.features}>
        <motion.div 
          className={`${styles.featureCard} glass-card`}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles.featureIcon}>
            <Zap size={24} />
          </div>
          <h3 className={styles.featureTitle}>Instant Generation</h3>
          <p className={styles.featureDesc}>
            Get a beautifully formatted, highly tailored CV in seconds. No more spending hours rewriting bullet points for every application.
          </p>
        </motion.div>

        <motion.div 
          className={`${styles.featureCard} glass-card`}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className={styles.featureIcon}>
            <Target size={24} />
          </div>
          <h3 className={styles.featureTitle}>Laser Targeted</h3>
          <p className={styles.featureDesc}>
            Our AI analyzes the job description to highlight your most relevant experience and match critical keywords exactly.
          </p>
        </motion.div>

        <motion.div 
          className={`${styles.featureCard} glass-card`}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className={styles.featureIcon}>
            <Shield size={24} />
          </div>
          <h3 className={styles.featureTitle}>ATS Friendly</h3>
          <p className={styles.featureDesc}>
            Export to clean, single-column PDF formats that Applicant Tracking Systems can easily parse without formatting errors.
          </p>
        </motion.div>
      </section>
    </div>
  );
}
