import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadGeistMono } from "@remotion/google-fonts/GeistMono";

const geist = loadGeist("normal", { weights: ["400", "600", "700", "800"], subsets: ["latin"] });
const geistMono = loadGeistMono("normal", { weights: ["500", "600"], subsets: ["latin"] });

export const GEIST = geist.fontFamily;
export const GEIST_MONO = geistMono.fontFamily;
