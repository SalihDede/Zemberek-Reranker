import py4j.GatewayServer;
import zemberek.morphology.TurkishMorphology;
import zemberek.morphology.analysis.WordAnalysis;
import zemberek.morphology.analysis.SingleAnalysis;
import java.util.List;
import java.util.ArrayList;

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

    public static void main(String[] args) throws Exception {
        ZemberekGateway gateway = new ZemberekGateway();
        GatewayServer server = new GatewayServer(gateway);
        server.start();
        System.out.println("Zemberek Gateway başlatıldı.");
    }
}
