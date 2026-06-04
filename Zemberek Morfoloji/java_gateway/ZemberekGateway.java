import py4j.GatewayServer;
import zemberek.morphology.TurkishMorphology;
import zemberek.morphology.analysis.WordAnalysis;
import zemberek.morphology.analysis.SingleAnalysis;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.LinkedHashMap;

public class ZemberekGateway {
    private TurkishMorphology morphology;

    public ZemberekGateway() throws Exception {
        this.morphology = TurkishMorphology.createWithDefaults();
    }

    public WordAnalysis analyze(String word) {
        return morphology.analyze(word);
    }

    public List<WordAnalysis> analyzeSentence(String sentence) {
        return morphology.analyzeSentence(sentence);
    }

    public List<String> getAnalysisResults(String word) {
        WordAnalysis analysis = morphology.analyze(word);
        List<String> results = new ArrayList<>();
        for (SingleAnalysis sa : analysis) {
            results.add(sa.formatLong());
        }
        return results;
    }

    public Map<String, List<String>> getSentenceAnalyses(String sentence) {
        List<WordAnalysis> analyses = morphology.analyzeSentence(sentence);
        Map<String, List<String>> result = new LinkedHashMap<>();
        for (WordAnalysis wa : analyses) {
            List<String> candidates = new ArrayList<>();
            for (SingleAnalysis sa : wa) {
                candidates.add(sa.formatLong());
            }
            if (!candidates.isEmpty()) {
                result.put(wa.getInput(), candidates);
            }
        }
        return result;
    }

    public static void main(String[] args) throws Exception {
        ZemberekGateway gateway = new ZemberekGateway();
        GatewayServer server = new GatewayServer(gateway);
        server.start();
        System.out.println("Zemberek Gateway başlatıldı.");
    }
}
