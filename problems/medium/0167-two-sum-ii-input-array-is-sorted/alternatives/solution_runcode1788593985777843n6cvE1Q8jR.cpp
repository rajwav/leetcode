class Solution {
public:
    vector<int> teosum(vector<int>& a, int target) {
        int i = 0;
        int j = a.size() - 1;

        while (i < j) {
            int sum = a[i] + a[j];

            if (sum == target) {
                return{i+1, j+1};
            }
            if (sum < target) {
                i++;
            }
            else {
                j--;
            }
        }

        return {};
    }
};
