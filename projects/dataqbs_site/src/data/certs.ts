import type { Certification } from '../lib/types';

export const certifications: Certification[] = [
  {
    name: 'SnowPro Specialty: Generative AI (GES-C01)',
    shortName: 'Snowflake GenAI',
    issuer: 'Snowflake',
    year: 2026,
    credentialUrl: '', // ← UPDATE when available
    logo: '❄️',
  },
  {
    name: 'Microsoft Certified: Azure Data Engineer Associate',
    shortName: 'Azure Data Eng.',
    issuer: 'Microsoft',
    year: 2023, // ← UPDATE
    credentialUrl: '',
    logo: '📊',
  },
  {
    name: 'Microsoft Certified: Azure Fundamentals (AZ-900)',
    shortName: 'Azure Fundamentals',
    issuer: 'Microsoft',
    year: 2022, // ← UPDATE
    credentialUrl: '',
    logo: '☁️',
  },
  {
    name: 'MCSA: SQL 2016 Database Development',
    shortName: 'MCSA SQL',
    issuer: 'Microsoft',
    year: 2019, // ← UPDATE
    credentialUrl: '',
    logo: '🗄️',
  },
];
