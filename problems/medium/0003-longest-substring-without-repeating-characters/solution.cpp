class Solution {
public:
    int lengthOfLongestSubstring(string s) {

        unordered_map<char, int> lastSeen;

        int left = 0;
        int maxLen = 0;

        for (int right = 0; right < s.length(); right++) {

            char ch = s[right];

            if (lastSeen.find(ch) != lastSeen.end()) {
                left = max(left, lastSeen[ch] + 1);
            }

            lastSeen[ch] = right;

            maxLen = max(maxLen, right - left + 1);
        }

        return maxLen;
    }
};
