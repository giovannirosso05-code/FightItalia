// Dati curati a mano (non da scraping automatico) sulle principali
// organizzazioni MMA europee: campioni attuali per ciascuna. KSW e
// Oktagon MMA hanno anche roster ed eventi completi scaricati da
// Wikipedia (vedi organizzazione.html?org=ksw / ?org=oktagon) — Cage
// Warriors e ARES FC non hanno una pagina "List of current fighters" su
// Wikipedia, quindi per loro c'e' solo questo elenco campioni.

export const ORGANIZZAZIONI = [
  {
    id: "ksw",
    nome: "KSW",
    nomeCompleto: "Konfrontacja Sztuk Walki",
    paese: "🇵🇱 Polonia",
    fondata: 2004,
    descrizione: "La più grande organizzazione MMA polacca e la principale d'Europa dalla sua fondazione.",
    link: "https://en.wikipedia.org/wiki/Konfrontacja_Sztuk_Walki",
    campioni: [
      { categoria: "Leggeri (Lightweight)", nome: "Salahdine Parnasse" },
      { categoria: "Piuma (Featherweight)", nome: "Salahdine Parnasse" },
      { categoria: "Welter (Welterweight)", nome: "Adrian Bartosiński" },
      { categoria: "Medi (Middleweight)", nome: "Paweł Pawlak" },
      { categoria: "Mediomassimi (Light Heavyweight)", nome: "Rafał Haratyk" },
      { categoria: "Gallo (Bantamweight)", nome: "Sebastian Przybysz" },
    ],
  },
  {
    id: "oktagon",
    nome: "Oktagon MMA",
    nomeCompleto: "Oktagon MMA",
    paese: "🇨🇿🇸🇰 Rep. Ceca / Slovacchia",
    fondata: 2016,
    descrizione: "Nata dall'unione ceco-slovacca, ha battuto il record mondiale di affluenza per un evento MMA nell'autunno 2024 (~60.000 spettatori a Francoforte).",
    link: "https://en.wikipedia.org/wiki/Oktagon_MMA",
    campioni: [
      { categoria: "Piuma (Featherweight)", nome: "Machaev" },
      { categoria: "Welter (Welterweight)", nome: "Kaik Brito" },
      { categoria: "Medi (Middleweight)", nome: "Kerim Engizek" },
      { categoria: "Leggeri (Lightweight)", nome: "Mateusz Legierski" },
    ],
  },
  {
    nome: "Cage Warriors",
    nomeCompleto: "Cage Warriors Fighting Championship",
    paese: "🇬🇧 Regno Unito",
    fondata: 1997,
    descrizione: "La più storica organizzazione europea: trampolino di lancio per campioni UFC come Conor McGregor e Michael Bisping.",
    link: "https://en.wikipedia.org/wiki/Cage_Warriors",
    campioni: [
      { categoria: "Mosca (Flyweight)", nome: "Nicolas Leblond" },
      { categoria: "Gallo (Bantamweight)", nome: "Weslley Maia" },
      { categoria: "Piuma (Featherweight)", nome: "Nik Bagley" },
      { categoria: "Leggeri (Lightweight)", nome: "Omiel Brown" },
      { categoria: "Welter (Welterweight)", nome: "Justin Burlinson" },
      { categoria: "Medi (Middleweight)", nome: "Dario Bellandi" },
    ],
  },
  {
    nome: "ARES FC",
    nomeCompleto: "ARES Fighting Championship",
    paese: "🇫🇷 Francia",
    fondata: 2020,
    descrizione: "La principale organizzazione MMA francese. Categorie di peso e regole allineate a UFC per facilitare il passaggio dei giovani talenti.",
    link: "https://en.wikipedia.org/wiki/Ares_Fighting_Championship",
    campioni: [
      { categoria: "Piuma (Featherweight)", nome: "Josh O'Connor" },
      { categoria: "Welter (Welterweight)", nome: "Jordan Zébo" },
      { categoria: "Medi (Middleweight)", nome: "Virgil Augen" },
      { categoria: "Mediomassimi (Light Heavyweight)", nome: "Moustapha Diakhaté" },
      { categoria: "Massimi (Heavyweight)", nome: "Xavier Lessou" },
    ],
  },
];
