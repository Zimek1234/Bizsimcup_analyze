import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'ERPsim · Přehled hry',description:'Týmová analytika ERPsim Manufacturing'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="cs"><body>{children}</body></html>;}
